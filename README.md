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
