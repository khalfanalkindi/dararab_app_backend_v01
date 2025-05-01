release: python manage.py collectstatic --noinput && python manage.py migrate && echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')" | python manage.py shell
web: gunicorn backend.wsgi
