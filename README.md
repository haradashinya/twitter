## Dwitter ~ Twitter Clone by Django


Dwitter is sample app which use Django.


## SETUP
    pyvenv-3.4 venv
    source venv/bin/activate
    cd django-trunk; python setup.py install
    pip install -r requirements.txt
    python twitter_project/manage.py runserver


## DEPLOY It


Setting of nginx file is like this.

    server {
        listen 80;
        server_name  your_server_name;

        location /static {
            root /path/to/twitter/twitter_project/twitter_project;
        }

        location / {
            proxy_pass http://127.0.0.1:8001;
            }

    }

And type it to run server.

    gunicorn twitter_project.wsgi:application -c gunicorn.conf.py


