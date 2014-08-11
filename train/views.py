from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.shortcuts import render_to_response, get_object_or_404, redirect, render
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from accounts.models import UserProfile, Batch, Task, TaskSubmit
from accounts.views import login_view
from django.contrib.sessions.models import Session
from datetime import datetime, timedelta
from django.db import transaction
from django.db.models import Sum, Avg, F
import random
import string
import os
import fcntl
from django.core.files import locks
from django.utils.timezone import utc
from django.conf import settings
from decimal import *
import ast

# Core method
def work(request,task_id):
    num_users = UserProfile.objects.count();
    if num_users >= 60:
        return render_to_response('error.html', context_instance=RequestContext(request))
    print "giving !!!!!!"
    # Some user management with mturk
    workerId = request.GET.get('workerId')
    assignmentId = request.GET.get('assignmentId')
    print workerId
    if request.user.is_authenticated() == False:
        if workerId != None:
            print "new with id ", workerId
            user = authenticate(username=workerId, password="cool")
            if user is not None:
                print "user is back !"
                login(request, user)
            else:
                print "user is new: create him"
                user = User.objects.create_user(workerId, 'username@hitbit.co', "cool")
                user = authenticate(username=workerId, password="cool")
                login(request, user)
                user_profile = UserProfile.objects.create(user=request.user)
                user_profile.exp_type =  (user_profile.id % 3) +1
                user_profile.save()
        else:
            print "new without id"
            return render_to_response('welcome.html', context_instance=RequestContext(request))
    else: 
        print "super, user is back: ", request.user
    print "super, user is here: ", request.user
    if task_id == None:
        return render_to_response('error.html', context_instance=RequestContext(request))

    # get the user profile
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return HttpResponseRedirect(reverse('login_view'))

    print user_profile.id, "YOHO"
    # Get the batch:
    tuser = user_profile.exp_type 
    last_batch = user_profile.last_batch
    last_batch_seen = user_profile.last_batch_seen
    batch_to_run = 0
    
    if tuser == 1: # This guy switches ABABABAB
        if last_batch == 1:
            batch_to_run = 2
        else:
            batch_to_run = 1
        user_profile.last_batch_seen = 0
        user_profile.save()
    elif tuser == 2: # This guy does AAAABBBB
        if last_batch_seen >= 10:
            if last_batch == 1:
                batch_to_run = 2
            else:
                batch_to_run = 1
            user_profile.last_batch_seen = 0
            user_profile.save()
        else: 
            batch_to_run = last_batch
    else: 
        if last_batch_seen >= 25:
            if last_batch == 1:
                batch_to_run = 2
            else:
                batch_to_run = 1
            user_profile.last_batch_seen = 0
            user_profile.save()
        else: 
            batch_to_run = last_batch

    batch = Batch.objects.get(id = batch_to_run)

    print "Running batch:", batch, batch.bclass

    if assignmentId == "ASSIGNMENT_ID_NOT_AVAILABLE":
        return render_to_response('accept.html', {'user_profile':user_profile, 'batch': batch}, context_instance=RequestContext(request))

    # get the task
    from django.db import IntegrityError
    task = random.choice(Task.objects.filter(batch=batch))
    try: 
        assigned, created= TaskSubmit.objects.get_or_create(user=request.user,task=task, elapsed=0)
    except IntegrityError as e:
        return render_to_response('done.html', {'user_profile':user_profile}, context_instance=RequestContext(request))

    print "Working on:", task

    # user_profile.last_batch = task.batch.id
    # user_profile.last_batch_seen += 1
    # user_profile.save()

    # Generate the next task and send it to the worker:
    if batch.bclass == "er_multi":
        print task.id, "!!!!!!", task.question
        items = ast.literal_eval(task.question)
        print "Items Set: ", items
        item = items[0]
        items = items[1:]
        return render_to_response('er.html', {'user_profile':user_profile, 'task':task, 'item':item, 'items':items, 'batch':batch}, 
            context_instance=RequestContext(request))
    elif batch.bclass == "classify":
        return render_to_response('flies.html', {'user_profile':user_profile, 'task':task, 'batch':batch}, 
            context_instance=RequestContext(request))
    else:
        return render_to_response('error.html', {'user_profile':user_profile}, context_instance=RequestContext(request))


# some actions
from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
@login_required
def submit(request, task_id):
    print "submitting !!!!!!"
    task = get_object_or_404(Task, pk=task_id)

    from django.core.exceptions import MultipleObjectsReturned
    print "submit" , task, task.id
    try:
        tasksubmit = TaskSubmit.objects.get(user=request.user,task=task)
    except TaskSubmit.DoesNotExist:
        # In case the person stayed too long and got dismissed
        return render_to_response('error.html', {'user_profile':user_profile}, context_instance=RequestContext(request))
    except MultipleObjectsReturned:
        tasksubmit = TaskSubmit.objects.filter(user=request.user,task=task)[0]
    tasksubmit.submittime = datetime.utcnow().replace(tzinfo=utc)
    start = tasksubmit.starttime
    end = tasksubmit.submittime
    print start
    print end
    tasksubmit.elapsed = (end-start).seconds+((end-start).microseconds/1e6)
    tasksubmit.save()
    user_profile = UserProfile.objects.get(user=request.user)
    user_profile.credit = user_profile.credit + tasksubmit.bonus
    user_profile.last_batch = task.batch.id
    user_profile.last_batch_seen += 1
    user_profile.save()
    return HttpResponse('', mimetype="application/javascript")

def welcome(request):
    num_users = UserProfile.objects.count();
    if num_users >= 60:
        return render_to_response('error.html', context_instance=RequestContext(request))
    print "welcome ! "
    batch = Batch.objects.get(id=1)
    return render_to_response('welcome.html', {'batch': batch}, context_instance=RequestContext(request))
