FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webapp/ ./webapp/
COPY entrypoint.sh /app/entrypoint.sh
COPY GuardianAgent-Photoroom.png ./webapp/static/images/logo.png

WORKDIR /app/webapp

RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "/app/entrypoint.sh"]
