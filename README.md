
## Twitter Clone by Django


## SETUP
    cd pyvenv-3.4 venv
    source venv/bin/activate
    cd django-trunk; python setup.py install
    pip install -r requirements.txt
    python twitter_project/manage.py runserver


## DEPLOY

    gunicorn twitter_project.wsgi:application -c gunicorn.conf.py

