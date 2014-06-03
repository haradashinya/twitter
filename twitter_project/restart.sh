fuser -k 8001/tcp;
source ../venv/bin/activate;
echo "DONE"
gunicorn twitter_project.wsgi:application -c gunicorn.conf.py  -D
echo "Finished Restarting"


