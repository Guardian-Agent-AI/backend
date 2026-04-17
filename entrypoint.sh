#!/bin/sh
set -e

echo "Running migrations..." joris@whale-academy.com
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating default admin user..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@guardian.com', 'admin123')
    print('Admin user created.')
else:
    print('Admin user already exists.')
# Ensure every user has a profile
from core.models import UserProfile
for u in User.objects.all():
    UserProfile.objects.get_or_create(user=u)
"

echo "Starting Gunicorn..."
exec gunicorn guardian_project.wsgi:application --bind 0.0.0.0:${PORT:-8000} --reload
