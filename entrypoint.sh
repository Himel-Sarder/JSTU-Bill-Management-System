#!/bin/sh

python manage.py makemigrations
python manage.py migrate

exec gunicorn bill_management.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --timeout 120
