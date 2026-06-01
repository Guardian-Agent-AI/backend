# Guardian Agent — Backend

Django backend and web interface for Guardian Agent.

## Stack

- Python 3.12 / Django 4.2 / Gunicorn
- PostgreSQL 16
- Docker Compose

## Run

```bash
docker compose up --build
```

App is available at **http://localhost:8000**

Admin panel: http://localhost:8000/admin  
Default credentials: `admin` / `admin123`

> Change `DJANGO_SECRET_KEY` in `docker-compose.yml` before deploying to production.

## Repository Structure

```
backend/
├── Dockerfile                        # Docker image definition
├── docker-compose.yml                # Service orchestration (app + postgres)
├── entrypoint.sh                     # Container startup script
├── requirements.txt                  # Python dependencies
├── Guardian.Desktop.exe              # Desktop client binary
└── webapp/
    ├── manage.py                     # Django management entry point
    ├── guardian_project/             # Django project config
    │   ├── settings.py
    │   ├── urls.py
    │   └── wsgi.py
    ├── core/                         # Main application
    │   ├── models.py                 # Database models
    │   ├── views.py                  # View logic
    │   ├── urls.py                   # URL routing
    │   ├── api.py                    # API endpoints
    │   ├── admin.py                  # Admin panel config
    │   ├── forms.py                  # Django forms
    │   ├── signals.py                # Model signals
    │   ├── migrations/               # Database migrations
    │   └── management/
    │       └── commands/
    │           └── seed_mock_data.py # Dev data seeder
    ├── static/
    │   ├── css/style.css
    │   ├── js/main.js
    │   └── images/logo.png
    └── templates/
        └── core/
            ├── base.html
            ├── landing.html
            ├── signin.html
            ├── signup.html
            ├── signup_success.html
            ├── settings.html
            └── install.html
```
