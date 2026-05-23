import json
import logging
from datetime import datetime, timezone as dt_timezone

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import Plan, UserProfile
from .models import Payment

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


# ─── Helpers ─────────────────────────────────────────────────────

def _get_or_create_stripe_customer(user):
    """Return the Stripe customer id for this user, creating it if needed."""
    profile = user.profile
    if profile.stripe_customer_id:
        return profile.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=user.get_full_name() or user.email,
        metadata={'user_id': str(user.id)},
    )
    profile.stripe_customer_id = customer.id
    profile.save(update_fields=['stripe_customer_id'])
    return customer.id


def _ts_to_dt(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=dt_timezone.utc)


# ─── Checkout ────────────────────────────────────────────────────

@login_required(login_url='signin')
def create_checkout_session(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id, is_active=True)

    if not plan.stripe_price_id:
        logger.error('Plan %s has no stripe_price_id — run `manage.py sync_stripe_prices` first', plan.id)
        return render(request, 'payments/error.html', {
            'error': 'This plan is not configured for billing yet. Please contact support.'
        }, status=503)

    # If the user already has an active sub, send them straight to the portal
    # to handle plan switches with proper proration / period-end semantics.
    profile = request.user.profile
    if profile.has_active_subscription and profile.stripe_subscription_id:
        return redirect('billing_portal')

    customer_id = _get_or_create_stripe_customer(request.user)

    try:
        checkout_session = stripe.checkout.Session.create(
            mode='subscription',
            customer=customer_id,
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            success_url=request.build_absolute_uri('/payments/success/?session_id={CHECKOUT_SESSION_ID}'),
            cancel_url=request.build_absolute_uri(f'/payments/cancel/?plan_id={plan_id}'),
            allow_promotion_codes=True,
            metadata={
                'user_id': str(request.user.id),
                'plan_id': str(plan_id),
            },
            subscription_data={
                'metadata': {
                    'user_id': str(request.user.id),
                    'plan_id': str(plan_id),
                },
            },
        )
    except stripe.error.StripeError as e:
        logger.error('Stripe error creating checkout session: %s', e)
        return render(request, 'payments/error.html', {'error': str(e)}, status=502)

    Payment.objects.create(
        user=request.user,
        amount=int(plan.price_monthly * 100),
        currency='eur',
        description=f'Guardian Agent – {plan.name} (subscription)',
        stripe_checkout_session_id=checkout_session.id,
        status=Payment.STATUS_PENDING,
    )

    return redirect(checkout_session.url, permanent=False)


# ─── Billing Portal (Stripe-hosted manage subscription page) ─────

@login_required(login_url='signin')
def billing_portal(request):
    profile = request.user.profile

    if not profile.stripe_customer_id:
        messages.info(request, 'You need an active subscription before you can manage it.')
        return redirect('settings')

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=profile.stripe_customer_id,
            return_url=request.build_absolute_uri('/settings/'),
        )
    except stripe.error.StripeError as e:
        logger.error('Stripe error creating billing portal session: %s', e)
        # Most common: portal not configured yet in Stripe Dashboard
        return render(request, 'payments/error.html', {
            'error': (
                'The billing portal is not configured yet. '
                'Visit https://dashboard.stripe.com/test/settings/billing/portal to enable it. '
                f'(Stripe error: {e})'
            )
        }, status=502)

    return redirect(portal_session.url, permanent=False)


# ─── Success / Cancel landing pages ──────────────────────────────

@login_required(login_url='signin')
def payment_success(request):
    session_id = request.GET.get('session_id', '')
    payment = None
    plan = None

    if session_id:
        payment = Payment.objects.filter(
            stripe_checkout_session_id=session_id,
            user=request.user,
        ).first()

        try:
            session = stripe.checkout.Session.retrieve(session_id)
            plan_id = session.metadata.get('plan_id')
            if plan_id:
                plan = Plan.objects.filter(id=plan_id, is_active=True).first()
        except stripe.error.StripeError:
            pass

    return render(request, 'payments/success.html', {
        'payment': payment,
        'plan': plan,
    })


@login_required(login_url='signin')
def payment_cancel(request):
    plan_id = request.GET.get('plan_id')
    plan = None
    if plan_id:
        plan = Plan.objects.filter(id=plan_id, is_active=True).first()
    return render(request, 'payments/cancel.html', {'plan': plan})


# ─── Webhook ─────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        logger.warning('STRIPE_WEBHOOK_SECRET not configured — skipping signature verification')
    else:
        try:
            stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.error.SignatureVerificationError:
            logger.warning('Invalid Stripe webhook signature')
            return HttpResponse('Invalid signature', status=400)
        except Exception as e:
            logger.error('Webhook error: %s', e)
            return HttpResponse(str(e), status=400)

    # Parse the raw payload as a plain dict so handlers can use .get()
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        return HttpResponse('Invalid payload', status=400)

    event_type = event.get('type', '')
    data_object = event.get('data', {}).get('object', {})

    logger.info('Received Stripe webhook: %s', event_type)

    try:
        if event_type == 'checkout.session.completed':
            _handle_checkout_completed(data_object)
        elif event_type in ('customer.subscription.created', 'customer.subscription.updated'):
            _handle_subscription_updated(data_object)
        elif event_type == 'customer.subscription.deleted':
            _handle_subscription_deleted(data_object)
        elif event_type == 'invoice.payment_succeeded':
            _handle_invoice_paid(data_object)
        elif event_type == 'invoice.payment_failed':
            _handle_invoice_failed(data_object)
    except Exception as e:
        logger.exception('Error handling Stripe event %s: %s', event_type, e)

    return HttpResponse(status=200)


# ─── Webhook handlers ────────────────────────────────────────────

def _handle_checkout_completed(session):
    """Initial checkout success — links the new subscription to the user."""
    session_id = session.get('id', '')
    subscription_id = session.get('subscription', '') or ''
    customer_id = session.get('customer', '') or ''
    metadata = session.get('metadata', {}) or {}
    user_id = metadata.get('user_id')
    plan_id = metadata.get('plan_id')

    # Mark the local Payment row as succeeded
    payment = Payment.objects.filter(stripe_checkout_session_id=session_id).first()
    if payment:
        payment.status = Payment.STATUS_SUCCEEDED
        payment.save(update_fields=['status', 'updated_at'])

    # Link customer + subscription to the user's profile
    profile = None
    if user_id:
        profile = UserProfile.objects.filter(user_id=user_id).first()
    if not profile and customer_id:
        profile = UserProfile.objects.filter(stripe_customer_id=customer_id).first()

    if not profile:
        logger.warning('Checkout session %s could not be linked to a UserProfile', session_id)
        return

    if customer_id:
        profile.stripe_customer_id = customer_id
    if subscription_id:
        profile.stripe_subscription_id = subscription_id

    if plan_id:
        plan = Plan.objects.filter(id=plan_id).first()
        if plan:
            profile.plan = plan

    profile.subscription_status = UserProfile.SUB_STATUS_ACTIVE
    profile.save(update_fields=[
        'stripe_customer_id', 'stripe_subscription_id', 'plan', 'subscription_status'
    ])


def _handle_subscription_updated(subscription):
    """Stripe pushed an updated subscription state — sync it locally.

    This fires on: initial creation, plan changes (immediate or scheduled),
    cancellations (cancel_at_period_end), and period renewals.
    """
    sub_id = subscription.get('id', '')
    customer_id = subscription.get('customer', '')
    status = subscription.get('status', '')  # active, past_due, canceled, ...
    cancel_at_period_end = bool(subscription.get('cancel_at_period_end'))
    current_period_end = subscription.get('current_period_end')

    # Current price/plan
    items = (subscription.get('items') or {}).get('data', []) or []
    current_price_id = items[0].get('price', {}).get('id', '') if items else ''

    profile = _find_profile_by_sub_or_customer(sub_id, customer_id)
    if not profile:
        logger.warning('Subscription %s: no matching UserProfile found', sub_id)
        return

    # Map Stripe status → our local status
    if status == 'active':
        local_status = (UserProfile.SUB_STATUS_CANCELING if cancel_at_period_end
                        else UserProfile.SUB_STATUS_ACTIVE)
    elif status == 'past_due':
        local_status = UserProfile.SUB_STATUS_PAST_DUE
    elif status in ('canceled', 'unpaid', 'incomplete_expired'):
        local_status = UserProfile.SUB_STATUS_CANCELED
    else:
        local_status = profile.subscription_status

    # Match the current price back to a local Plan
    matched_plan = None
    if current_price_id:
        matched_plan = Plan.objects.filter(stripe_price_id=current_price_id).first()

    profile.stripe_subscription_id = sub_id
    if customer_id:
        profile.stripe_customer_id = customer_id
    profile.subscription_status = local_status
    profile.current_period_end = _ts_to_dt(current_period_end)
    if matched_plan:
        profile.plan = matched_plan
    profile.save()


def _handle_subscription_deleted(subscription):
    """Subscription fully ended (either at period end after cancellation, or hard-cancelled)."""
    sub_id = subscription.get('id', '')
    customer_id = subscription.get('customer', '')

    profile = _find_profile_by_sub_or_customer(sub_id, customer_id)
    if not profile:
        return

    profile.subscription_status = UserProfile.SUB_STATUS_CANCELED
    profile.plan = None
    profile.save(update_fields=['subscription_status', 'plan'])


def _handle_invoice_paid(invoice):
    """Recurring monthly charge succeeded — log a Payment row."""
    customer_id = invoice.get('customer', '')
    amount_paid = invoice.get('amount_paid', 0)
    if not customer_id or not amount_paid:
        return

    profile = UserProfile.objects.filter(stripe_customer_id=customer_id).first()
    if not profile:
        return

    Payment.objects.create(
        user=profile.user,
        amount=int(amount_paid),
        currency=invoice.get('currency', 'eur'),
        description=f'Guardian Agent – {profile.plan.name if profile.plan else "subscription"} (renewal)',
        status=Payment.STATUS_SUCCEEDED,
    )


def _handle_invoice_failed(invoice):
    customer_id = invoice.get('customer', '')
    if not customer_id:
        return
    profile = UserProfile.objects.filter(stripe_customer_id=customer_id).first()
    if not profile:
        return
    profile.subscription_status = UserProfile.SUB_STATUS_PAST_DUE
    profile.save(update_fields=['subscription_status'])


def _find_profile_by_sub_or_customer(sub_id, customer_id):
    profile = None
    if sub_id:
        profile = UserProfile.objects.filter(stripe_subscription_id=sub_id).first()
    if not profile and customer_id:
        profile = UserProfile.objects.filter(stripe_customer_id=customer_id).first()
    return profile
