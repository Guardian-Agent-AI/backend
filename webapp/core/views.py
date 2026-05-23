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
from .models import Plan, UserProfile, Child, Device, Incident, CommunityThreatStat, CommunityPeakTimeStat
from .forms import RegistrationForm, LoginForm, ContactForm, AccountSettingsForm, ChangePasswordForm, ChildForm


# ─── Landing ──────────────────────────────────────────────
def landing(request):
    if request.user.is_authenticated and request.method == 'GET':
        return redirect('dashboard')

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
        # Already logged in → assign plan and go to settings
        if plan:
            profile = request.user.profile
            profile.plan = plan
            profile.save()
            messages.success(request, f'You are now on the {plan.name} plan!')
            return redirect('settings')
        return redirect('settings')

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
        return redirect('settings')

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
                next_url = request.GET.get('next', 'settings')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid email or password.')

    return render(request, 'core/signin.html', {'form': form})


# ─── Auth: Sign Out ──────────────────────────────────────
def signout_view(request):
    logout(request)
    messages.success(request, 'You have been signed out.')
    return redirect('landing')


# ─── Dashboard (minimal welcome) ──────────────────────────
@login_required(login_url='signin')
def dashboard(request):
    return render(request, 'core/dashboard.html')


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
        alerts_24h    = selected_child.incidents.filter(detected_at__gte=last_24h).count()
        alerts_7d     = selected_child.incidents.filter(detected_at__gte=last_7d).count()
        recent_alerts = selected_child.incidents.filter(detected_at__gte=last_7d).order_by('-detected_at')[:15]

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
    devices = Device.objects.filter(child__parent=profile).order_by('-last_seen_at', 'name')

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
