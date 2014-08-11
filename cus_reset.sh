heroku pg:reset DATABASE_URL --confirm radiant-eyrie-1479 
heroku run python manage.py syncdb
heroku run python manage.py loaddata fixtures/butterflies.json
heroku run python manage.py loaddata fixtures/er.json
