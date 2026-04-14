"""
Guardian Agent – REST API
Endpoints for the desktop application to authenticate users and retrieve account info.
All API endpoints return JSON.
"""

import json
import hashlib
import hmac
import time

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from .models import UserProfile


def _token_for_user(user):
    """Generate a simple HMAC token for API auth (user_id:timestamp:signature)."""
    from django.conf import settings
    ts = str(int(time.time()))
    payload = f"{user.pk}:{ts}"
    sig = hmac.new(
        settings.SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()[:32]
    return f"{user.pk}:{ts}:{sig}"


def _user_from_token(token):
    """Validate token and return User or None."""
    from django.conf import settings
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return None
        uid, ts, sig = parts
        payload = f"{uid}:{ts}"
        expected = hmac.new(
            settings.SECRET_KEY.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()[:32]
        if not hmac.compare_digest(sig, expected):
            return None
        # Token valid for 30 days
        if int(time.time()) - int(ts) > 30 * 86400:
            return None
        return User.objects.select_related('profile__plan').get(pk=int(uid))
    except (User.DoesNotExist, ValueError):
        return None


def _require_api_auth(view_func):
    """Decorator that validates Bearer token and injects request.api_user."""
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Authentication required.'}, status=401)
        token = auth_header[7:]
        user = _user_from_token(token)
        if user is None:
            return JsonResponse({'error': 'Invalid or expired token.'}, status=401)
        request.api_user = user
        return view_func(request, *args, **kwargs)
    return wrapper


def _profile_json(user):
    """Serialize user + profile to dict."""
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = None

    data = {
        'id': user.pk,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone_number': profile.phone_number if profile else '',
        'children_count': profile.children_count if profile else 0,
        'signed_up_at': profile.signed_up_at.isoformat() if profile else None,
        'plan': None,
    }
    if profile and profile.plan:
        data['plan'] = {
            'id': profile.plan.pk,
            'name': profile.plan.name,
            'price_monthly': str(profile.plan.price_monthly),
            'max_devices': profile.plan.max_devices,
            'max_children': profile.plan.max_children,
        }
    return data


# ─── POST /api/auth/login/ ───────────────────────────────
@csrf_exempt
@require_POST
def api_login(request):
    """Authenticate with email + password, receive a token."""
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    email = body.get('email', '').strip()
    password = body.get('password', '')

    if not email or not password:
        return JsonResponse({'error': 'Email and password are required.'}, status=400)

    user = authenticate(request, username=email, password=password)
    if user is None:
        return JsonResponse({'error': 'Invalid credentials.'}, status=401)

    return JsonResponse({
        'token': _token_for_user(user),
        'user': _profile_json(user),
    })


# ─── GET /api/auth/me/ ───────────────────────────────────
@csrf_exempt
@require_GET
@_require_api_auth
def api_me(request):
    """Return the authenticated user's profile."""
    return JsonResponse({'user': _profile_json(request.api_user)})


# ─── GET /api/plans/ ─────────────────────────────────────
@csrf_exempt
@require_GET
def api_plans(request):
    """List all active plans (public)."""
    from .models import Plan
    plans = Plan.objects.filter(is_active=True).order_by('price_monthly')
    return JsonResponse({'plans': [
        {
            'id': p.pk,
            'name': p.name,
            'price_monthly': str(p.price_monthly),
            'max_devices': p.max_devices,
            'max_children': p.max_children,
            'description': p.description,
            'features': p.feature_list(),
        }
        for p in plans
    ]})
