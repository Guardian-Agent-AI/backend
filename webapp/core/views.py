from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.conf import settings as django_settings
from django.http import FileResponse, Http404
from pathlib import Path
from datetime import timedelta
from django.utils import timezone
from .models import Plan, UserProfile, Child, AlertEvent, CommunityThreatStat, CommunityPeakTimeStat, Device
from .forms import RegistrationForm, LoginForm, ContactForm, AccountSettingsForm, ChangePasswordForm, ChildForm


# ─── Landing ──────────────────────────────────────────────
def landing(request):
    plans = Plan.objects.filter(is_active=True).order_by('price_monthly')
    contact_form = ContactForm()

    if request.method == 'POST' and 'contact_submit' in request.POST:
        contact_form = ContactForm(request.POST)
        if contact_form.is_valid():
            contact_form.save()
            messages.success(request, 'Thanks for reaching out! We\'ll get back to you soon.')
            return redirect('landing')

    return render(request, 'core/landing.html', {
        'plans': plans,
        'contact_form': contact_form,
    })


# ─── Auth: Sign Up ───────────────────────────────────────
def signup_view(request, plan_id=None):
    plan = None
    if plan_id:
        plan = get_object_or_404(Plan, id=plan_id, is_active=True)

    if request.user.is_authenticated:
        # Already logged in → assign plan and go to dashboard
        if plan:
            profile = request.user.profile
            profile.plan = plan
            profile.save()
            messages.success(request, f'You are now on the {plan.name} plan!')
            return redirect('dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['email'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.phone_number = form.cleaned_data['phone_number']
            profile.plan = plan
            profile.children_count = form.cleaned_data['children_count']
            profile.save()
            login(request, user)
            return redirect('install')
    else:
        form = RegistrationForm()

    return render(request, 'core/signup.html', {
        'form': form,
        'plan': plan,
    })


# ─── Auth: Sign In ───────────────────────────────────────
def signin_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            # Support users whose username != email (e.g. created via Django admin)
            user_qs = User.objects.filter(email=email)
            if user_qs.exists():
                username = user_qs.first().username
            else:
                username = email
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid email or password.')

    return render(request, 'core/signin.html', {'form': form})


# ─── Auth: Sign Out ──────────────────────────────────────
def signout_view(request):
    logout(request)
    messages.success(request, 'You have been signed out.')
    return redirect('landing')


# ─── Dashboard ────────────────────────────────────────────
_MOCK_ALERTS = [
    {'badge_class': 'secondary', 'icon': 'fa-share-alt',     'display_category': 'Social Media',     'game_name': 'Roblox',    'timestamp_str': '1 day ago',  'sms_message': 'Guardian Alert: A social media solicitation was detected on Roblox. Another player asked Emma to add them on Snapchat. They are attempting to move the conversation off-platform.'},
    {'badge_class': 'warning',   'icon': 'fa-id-card',       'display_category': 'Personal Info',    'game_name': 'Minecraft', 'timestamp_str': '4 days ago', 'sms_message': 'Guardian Alert: A personal information request was detected on Minecraft. A player asked "what school do you go to?" Personal details were directly solicited.'},
    {'badge_class': 'danger',    'icon': 'fa-map-marker-alt','display_category': 'Meeting Request',  'game_name': 'Fortnite',  'timestamp_str': '6 days ago', 'sms_message': 'Guardian Alert: A meeting request was detected in your child\'s chat on Fortnite. Another player suggested "we should hang out sometime." An in-person meetup was proposed.'},
]

_MOCK_THREAT_STATS = [
    {'display_label': 'Social Media Solicitation', 'icon': 'fa-share-alt',          'count': 312, 'pct': 100},
    {'display_label': 'Personal Info Request',     'icon': 'fa-id-card',            'count': 247, 'pct': 79},
    {'display_label': 'Meeting Request',           'icon': 'fa-map-marker-alt',     'count': 189, 'pct': 61},
    {'display_label': 'Grooming Language',         'icon': 'fa-exclamation-triangle','count': 143, 'pct': 46},
    {'display_label': 'Secrecy Request',           'icon': 'fa-user-secret',        'count':  98, 'pct': 31},
    {'display_label': 'Photo/Video Request',       'icon': 'fa-camera',             'count':  76, 'pct': 24},
    {'display_label': 'Threats / Bullying',        'icon': 'fa-fist-raised',        'count':  54, 'pct': 17},
    {'display_label': 'Gift / Bribery',            'icon': 'fa-gift',               'count':  38, 'pct': 12},
]

_MOCK_PEAK_TIMES = [
    {'label': '12am–3am', 'count':  14, 'pct':  5},
    {'label': '3am–6am',  'count':   6, 'pct':  2},
    {'label': '6am–9am',  'count':  19, 'pct':  6},
    {'label': '9am–12pm', 'count':  48, 'pct': 16},
    {'label': '12pm–3pm', 'count':  93, 'pct': 32},
    {'label': '3pm–6pm',  'count': 178, 'pct': 61},
    {'label': '6pm–9pm',  'count': 294, 'pct': 100},
    {'label': '9pm–12am', 'count': 251, 'pct': 85},
]


@login_required(login_url='signin')
def dashboard(request):
    recent_games = [
        {'name': 'Fortnite',      'last_played_str': '3 hours ago',  'total_minutes': 145},
        {'name': 'Roblox',        'last_played_str': '1 day ago',    'total_minutes': 225},
        {'name': 'Minecraft',     'last_played_str': '2 days ago',   'total_minutes': 170},
        {'name': 'Valorant',      'last_played_str': '3 days ago',   'total_minutes': 110},
        {'name': 'Rocket League', 'last_played_str': '5 days ago',   'total_minutes':  45},
        {'name': 'FIFA 25',       'last_played_str': '6 days ago',   'total_minutes':  35},
    ]
    max_game_minutes = max(g['total_minutes'] for g in recent_games)
    return render(request, 'core/dashboard.html', {
        'children':          [type('Child', (), {'id': 1, 'name': 'Emma', 'age': 11})()],
        'selected_child':    type('Child', (), {'id': 1, 'name': 'Emma', 'age': 11})(),
        'alerts_24h':        1,
        'alerts_7d':         3,
        'sessions_7d':       14,
        'playtime_7d':       625,
        'recent_alerts':     _MOCK_ALERTS,
        'recent_games':      recent_games,
        'max_game_minutes':  max_game_minutes,
    })


@login_required(login_url='signin')
def dashboard_live(request):
    profile = request.user.profile
    children = list(profile.children.order_by('name'))

    selected_child = None
    selected_child_id = request.GET.get('child')
    if children:
        if selected_child_id:
            selected_child = next((c for c in children if str(c.id) == selected_child_id), children[0])
        else:
            selected_child = children[0]

    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d  = now - timedelta(days=7)

    alerts_24h    = 0
    alerts_7d     = 0
    recent_alerts = []
    recent_games  = []
    sessions_7d   = 0
    playtime_7d   = 0

    if selected_child:
        alerts_24h    = selected_child.alerts.filter(timestamp__gte=last_24h).count()
        alerts_7d     = selected_child.alerts.filter(timestamp__gte=last_7d).count()
        recent_alerts = selected_child.alerts.filter(timestamp__gte=last_7d).order_by('-timestamp')[:15]

        all_sessions = selected_child.sessions.filter(started_at__gte=last_7d)
        sessions_7d  = all_sessions.count()
        playtime_7d  = sum(s.duration_minutes for s in all_sessions)

        seen: dict = {}
        for s in all_sessions.order_by('-started_at'):
            if s.game_name not in seen:
                seen[s.game_name] = {'last_played': s.started_at, 'total_minutes': 0}
            seen[s.game_name]['total_minutes'] += s.duration_minutes
        recent_games = [{'name': k, **v} for k, v in seen.items()]

    threat_stats = list(CommunityThreatStat.objects.all())
    peak_time_stats = list(CommunityPeakTimeStat.objects.all())

    max_threat = max((s.count for s in threat_stats), default=1)
    max_peak   = max((s.count for s in peak_time_stats), default=1)
    for s in threat_stats:
        s.pct = round(s.count / max_threat * 100)
    for s in peak_time_stats:
        s.pct = round(s.count / max_peak * 100)

    return render(request, 'core/dashboard.html', {
        'children':         children,
        'selected_child':   selected_child,
        'alerts_24h':       alerts_24h,
        'alerts_7d':        alerts_7d,
        'recent_alerts':    recent_alerts,
        'recent_games':     recent_games,
        'sessions_7d':      sessions_7d,
        'playtime_7d':      playtime_7d,
        'threat_stats':     threat_stats,
        'peak_time_stats':  peak_time_stats,
    })


# ─── Choose / Change Plan ────────────────────────────────
@login_required(login_url='signin')
def choose_plan(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id, is_active=True)
    profile = request.user.profile
    profile.plan = plan
    profile.save()
    messages.success(request, f'You are now subscribed to the {plan.name} plan!')
    return redirect('settings')


# ─── Settings ─────────────────────────────────────────────
@login_required(login_url='signin')
def settings_view(request):
    profile = request.user.profile
    plans = Plan.objects.filter(is_active=True).order_by('price_monthly')
    account_success = False
    password_success = False

    account_form = AccountSettingsForm(user=request.user, initial={
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
        'phone_number': profile.phone_number,
    })
    password_form = ChangePasswordForm()
    child_form = ChildForm()

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'account':
            account_form = AccountSettingsForm(request.POST, user=request.user)
            if account_form.is_valid():
                request.user.first_name = account_form.cleaned_data['first_name']
                request.user.last_name = account_form.cleaned_data['last_name']
                request.user.email = account_form.cleaned_data['email']
                request.user.username = account_form.cleaned_data['email']
                request.user.save()
                profile.phone_number = account_form.cleaned_data['phone_number']
                profile.save()
                account_success = True

        elif form_type == 'password':
            password_form = ChangePasswordForm(request.POST)
            if password_form.is_valid():
                if not request.user.check_password(password_form.cleaned_data['current_password']):
                    password_form.add_error('current_password', 'Incorrect password.')
                else:
                    request.user.set_password(password_form.cleaned_data['new_password'])
                    request.user.save()
                    login(request, request.user)
                    password_success = True

        elif form_type == 'add_child':
            child_form = ChildForm(request.POST)
            if child_form.is_valid():
                child = child_form.save(commit=False)
                child.parent = profile
                child.save()
                messages.success(request, f'{child.name} has been added.')
                return redirect('settings')

        elif form_type == 'remove_child':
            child_id = request.POST.get('child_id')
            if child_id:
                Child.objects.filter(id=child_id, parent=profile).delete()
                messages.success(request, 'Child removed.')
                return redirect('settings')

    children = profile.children.order_by('name')
    devices = profile.devices.order_by('-last_seen', 'name')

    return render(request, 'core/settings.html', {
        'profile': profile,
        'plans': plans,
        'account_form': account_form,
        'password_form': password_form,
        'child_form': child_form,
        'children': children,
        'devices': devices,
        'account_success': account_success,
        'password_success': password_success,
    })


# ─── Install Page ─────────────────────────────────────────
@login_required(login_url='signin')
def install_page(request):
    return render(request, 'core/install.html')


# ─── Download ─────────────────────────────────────────────
DOWNLOAD_FILES = {
    'windows': 'downloads/GuardianAgentSetup.exe',
}

@login_required(login_url='signin')
def download_app(request, platform):
    relative_path = DOWNLOAD_FILES.get(platform)
    if not relative_path:
        raise Http404('Platform not available.')
    file_path = Path(django_settings.STATICFILES_DIRS[0]) / relative_path
    if not file_path.is_file():
        raise Http404('File not found.')
    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_path.name)
