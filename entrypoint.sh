#!/bin/sh
set -eu

python manage.py migrate --noinput

python manage.py shell <<'PY'
import os

from django.contrib.auth import get_user_model

username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
if username and password:
    User = get_user_model()
    user, _ = User.objects.get_or_create(username=username)
    user.email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
    user.first_name = os.environ.get('DJANGO_SUPERUSER_NICKNAME', '')[:150]
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.set_password(password)
    user.save()
PY

exec gunicorn drone.wsgi:application --bind 0.0.0.0:${PORT:-8000} --access-logfile -

