#!/bin/sh
set -eu

python manage.py migrate --noinput
exec gunicorn viewer_backend.wsgi:application --bind 0.0.0.0:8000
