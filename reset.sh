dropdb train
createdb train
./manage.py syncdb
python manage.py loaddata fixtures/butterflies.json
python manage.py loaddata fixtures/er.json
