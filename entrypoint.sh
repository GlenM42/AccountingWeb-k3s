#!/bin/sh
set -e

uv run python manage.py migrate --no-input
uv run python manage.py collectstatic --no-input

uv run gunicorn AccountingWeb.wsgi:application --bind 0.0.0.0:8000 --workers 4
