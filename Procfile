web: gunicorn -w 4 -b 0.0.0.0:$PORT src.app:app
worker: celery -A src.async_classifier.celery_app worker --loglevel=info --concurrency=4
beat: celery -A src.async_classifier.celery_app beat --loglevel=info
