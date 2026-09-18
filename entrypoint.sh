#!/bin/bash
set -e

echo "Waiting for database at ${DB_HOST}:${DB_PORT}..."
while ! nc -z "${DB_HOST}" "${DB_PORT:-3306}"; do
  sleep 1
done
echo "Database is up."

python manage.py migrate --noinput

exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
