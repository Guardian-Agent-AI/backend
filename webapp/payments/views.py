import json
import logging

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import Plan
from .models import Payment

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required(login_url='signin')
def create_checkout_session(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id, is_active=True)

    # Price in cents
    amount_cents = int(plan.price_monthly * 100)

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'unit_amount': amount_cents,
                    'product_data': {
                        'name': f'Guardian Agent – {plan.name}',
                        'description': plan.description or f'Monthly subscription to the {plan.name} plan.',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri(f'/payments/success/?session_id={{CHECKOUT_SESSION_ID}}'),
            cancel_url=request.build_absolute_uri(f'/payments/cancel/?plan_id={plan_id}'),
            customer_email=request.user.email,
            metadata={
                'user_id': str(request.user.id),
                'plan_id': str(plan_id),
            },
        )
    except stripe.error.StripeError as e:
        logger.error('Stripe error creating checkout session: %s', e)
        return render(request, 'payments/error.html', {'error': str(e)}, status=502)

    payment = Payment.objects.create(
        user=request.user,
        amount=amount_cents,
        currency='eur',
        description=f'Guardian Agent – {plan.name} (monthly)',
        stripe_checkout_session_id=checkout_session.id,
        status=Payment.STATUS_PENDING,
    )

    return redirect(checkout_session.url, permanent=False)


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

        if payment and payment.status == Payment.STATUS_SUCCEEDED:
            # Retrieve the plan from metadata if available
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


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        logger.warning('STRIPE_WEBHOOK_SECRET not configured — skipping signature verification')
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return HttpResponse('Invalid payload', status=400)
    else:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.error.SignatureVerificationError:
            logger.warning('Invalid Stripe webhook signature')
            return HttpResponse('Invalid signature', status=400)
        except Exception as e:
            logger.error('Webhook error: %s', e)
            return HttpResponse(str(e), status=400)

    event_type = event.get('type', '')
    data_object = event.get('data', {}).get('object', {})

    try:
        if event_type == 'checkout.session.completed':
            _handle_checkout_completed(data_object)
        elif event_type == 'payment_intent.succeeded':
            _handle_payment_intent_succeeded(data_object)
        elif event_type == 'payment_intent.payment_failed':
            _handle_payment_intent_failed(data_object)
    except Exception as e:
        logger.error('Error handling Stripe event %s: %s', event_type, e)

    return HttpResponse(status=200)


def _handle_checkout_completed(session):
    session_id = session.get('id', '')
    payment_intent_id = session.get('payment_intent', '')
    plan_id = session.get('metadata', {}).get('plan_id')

    payment = Payment.objects.filter(stripe_checkout_session_id=session_id).first()
    if payment:
        payment.stripe_payment_intent_id = payment_intent_id or ''
        payment.status = Payment.STATUS_SUCCEEDED
        payment.save(update_fields=['stripe_payment_intent_id', 'status', 'updated_at'])

        if plan_id:
            plan = Plan.objects.filter(id=plan_id, is_active=True).first()
            if plan and hasattr(payment.user, 'profile'):
                payment.user.profile.plan = plan
                payment.user.profile.save(update_fields=['plan'])


def _handle_payment_intent_succeeded(payment_intent):
    intent_id = payment_intent.get('id', '')
    if not intent_id:
        return
    Payment.objects.filter(stripe_payment_intent_id=intent_id).update(status=Payment.STATUS_SUCCEEDED)


def _handle_payment_intent_failed(payment_intent):
    intent_id = payment_intent.get('id', '')
    if not intent_id:
        return
    Payment.objects.filter(stripe_payment_intent_id=intent_id).update(status=Payment.STATUS_FAILED)
