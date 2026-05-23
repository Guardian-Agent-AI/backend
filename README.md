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

## Stripe Payments

The app integrates with Stripe for subscription payments.

### Environment Variables

| Variable | Description |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe secret key (starts with `sk_test_` in dev) |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key (starts with `pk_test_` in dev) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret (starts with `whsec_`) |

Set these in your shell before running `docker compose up`:

```bash
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_PUBLISHABLE_KEY=pk_test_...
export STRIPE_WEBHOOK_SECRET=whsec_...
docker compose up --build
```

### Local Webhook Testing

Use the [Stripe CLI](https://stripe.com/docs/stripe-cli) to forward webhooks to your local server:

```bash
stripe listen --forward-to localhost:8000/payments/webhooks/stripe/
```

The CLI prints a webhook signing secret — copy it to `STRIPE_WEBHOOK_SECRET`.

### Test Cards

| Card | Result |
|---|---|
| `4242 4242 4242 4242` | Success |
| `4000 0000 0000 9995` | Declined |

Use any future expiry date and any 3-digit CVC.
