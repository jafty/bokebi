#!/bin/sh
set -eu
if [ "$#" -gt 0 ]; then
  exec "$@"
fi
python manage.py check_legacy_bokebi
python manage.py migrate --noinput
python manage.py migrate --database=contacts --noinput
python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --access-logfile - --error-logfile -
