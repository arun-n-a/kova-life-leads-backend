web: gunicorn runserver:app --workers 1 --threads 2 --log-file=-
worker: celery -A app.tasks worker -c 1 -B --loglevel=info
