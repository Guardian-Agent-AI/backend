from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator


phone_validator = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Enter a valid phone number (e.g. +1234567890).",
)


class Plan(models.Model):
    """Subscription plan offered to customers."""
    name = models.CharField(max_length=100)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2)
    max_devices = models.PositiveIntegerField(default=1)
    max_children = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    features = models.TextField(blank=True, help_text="One feature per line")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def feature_list(self):
        return [f.strip() for f in self.features.splitlines() if f.strip()]

    def __str__(self):
        return f"{self.name} – €{self.price_monthly}/mo"


class UserProfile(models.Model):
    """Extended profile for the parent/customer account."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=17, validators=[phone_validator], blank=True, default='')
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, default='')
    signed_up_at = models.DateTimeField(default=timezone.now)
    onboarded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.email})"


class Child(models.Model):
    """A child being monitored, linked to a parent UserProfile."""
    parent = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='children')
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (parent: {self.parent})"


class Device(models.Model):
    """A device with Guardian Agent installed, assigned to a child."""
    DEVICE_TYPES = [
        ('pc',      'PC'),
        ('console', 'Console'),
        ('tablet',  'Tablet'),
        ('phone',   'Phone'),
        ('other',   'Other'),
    ]
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='devices')
    name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, default='pc')
    os = models.CharField(max_length=100, blank=True, default='')
    agent_version = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_device_type_display()}) – {self.child.name}"


class GameSession(models.Model):
    """A single detected gaming session for a child on a device."""
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='sessions')
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    game_name = models.CharField(max_length=200)
    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    @property
    def duration_minutes(self):
        if self.ended_at:
            return max(0, int((self.ended_at - self.started_at).total_seconds() / 60))
        return 0

    def __str__(self):
        return f"{self.child.name} – {self.game_name} @ {self.started_at:%Y-%m-%d %H:%M}"


class Incident(models.Model):
    """A potential grooming/safety incident flagged by the local LLM."""
    SEVERITY_CHOICES = [
        ('low',      'Low'),
        ('medium',   'Medium'),
        ('high',     'High'),
        ('critical', 'Critical'),
    ]
    CATEGORY_CHOICES = [
        ('meeting_request',           'Meeting Request'),
        ('personal_info_request',     'Personal Info Request'),
        ('social_media_solicitation', 'Social Media Solicitation'),
        ('photo_video_request',       'Photo/Video Request'),
        ('grooming_language',         'Grooming Language'),
        ('secrecy_request',           'Secrecy Request'),
        ('threats_bullying',          'Threats / Bullying'),
        ('gift_bribery',              'Gift / Bribery'),
        ('other',                     'Other'),
    ]
    # (badge colour, FA icon, display label)
    CATEGORY_META = {
        'meeting_request':           ('danger',    'fa-map-marker-alt',      'Meeting Request'),
        'personal_info_request':     ('warning',   'fa-id-card',             'Personal Info'),
        'social_media_solicitation': ('info',      'fa-share-alt',           'Social Media'),
        'photo_video_request':       ('danger',    'fa-camera',              'Photo/Video'),
        'grooming_language':         ('danger',    'fa-exclamation-triangle', 'Grooming Language'),
        'secrecy_request':           ('warning',   'fa-user-secret',         'Secrecy Request'),
        'threats_bullying':          ('dark',      'fa-fist-raised',         'Threats/Bullying'),
        'gift_bribery':              ('secondary', 'fa-gift',                'Gift/Bribery'),
        'other':                     ('secondary', 'fa-question-circle',     'Other'),
    }
    SEVERITY_BADGE = {
        'low':      'secondary',
        'medium':   'warning',
        'high':     'danger',
        'critical': 'dark',
    }

    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='incidents', db_index=True)
    session = models.ForeignKey(GameSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidents')
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidents')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    category_label = models.CharField(max_length=200, blank=True)
    summary = models.TextField(help_text="LLM-generated summary of what happened")
    raw_context = models.TextField(blank=True, help_text="Flagged conversation snippet from on-device LLM")
    game_name = models.CharField(max_length=200)
    detected_at = models.DateTimeField(default=timezone.now, db_index=True)
    reviewed_by_parent = models.BooleanField(default=False)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_false_positive = models.BooleanField(default=False)

    class Meta:
        ordering = ['-detected_at']

    # Template-compatibility shims so dashboard templates work without changes
    @property
    def timestamp(self):
        return self.detected_at

    @property
    def badge_class(self):
        return self.SEVERITY_BADGE.get(self.severity, 'secondary')

    @property
    def icon(self):
        return self.CATEGORY_META.get(self.category, ('', 'fa-question-circle', ''))[1]

    @property
    def display_category(self):
        if self.category == 'other' and self.category_label:
            return self.category_label
        return self.CATEGORY_META.get(self.category, ('', '', self.get_category_display()))[2]

    @property
    def sms_message(self):
        return self.summary

    def __str__(self):
        return f"{self.child.name} – {self.display_category} @ {self.detected_at:%Y-%m-%d %H:%M}"


class Alert(models.Model):
    """A real-time notification sent to a parent when an incident is flagged."""
    ALERT_TYPES = [
        ('email', 'Email'),
        ('push',  'Push'),
        ('sms',   'SMS'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent',    'Sent'),
        ('failed',  'Failed'),
    ]

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, default='email')
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message_preview = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_alert_type_display()} – {self.incident} ({self.status})"


class WeeklyReport(models.Model):
    """A weekly summary email sent to a parent."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent',    'Sent'),
        ('failed',  'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weekly_reports')
    week_start = models.DateField()
    week_end = models.DateField()
    sent_at = models.DateTimeField(null=True, blank=True)
    email_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # Snapshot of that week's stats — preserved even if kids/devices change later
    report_data = models.JSONField(default=dict)

    class Meta:
        ordering = ['-week_start']

    def __str__(self):
        return f"Weekly Report for {self.user.email} ({self.week_start} → {self.week_end})"


class CommunityThreatStat(models.Model):
    """System-wide count of each threat category detected this week across all users."""
    category = models.CharField(max_length=50, choices=Incident.CATEGORY_CHOICES, unique=True)
    count = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-count']

    @property
    def display_label(self):
        return Incident.CATEGORY_META.get(self.category, ('', '', self.get_category_display()))[2]

    @property
    def icon(self):
        return Incident.CATEGORY_META.get(self.category, ('', 'fa-question-circle', ''))[1]

    def __str__(self):
        return f"{self.display_label}: {self.count}"


class CommunityPeakTimeStat(models.Model):
    """System-wide incident counts grouped by 3-hour time blocks."""
    hour_start = models.PositiveIntegerField(unique=True)  # 0, 3, 6, 9, 12, 15, 18, 21
    count = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['hour_start']

    @property
    def label(self):
        def fmt(h):
            return f"{h % 12 or 12}{'am' if h < 12 else 'pm'}"
        return f"{fmt(self.hour_start)}–{fmt((self.hour_start + 3) % 24)}"

    def __str__(self):
        return f"{self.label}: {self.count}"


class ContactMessage(models.Model):
    """Contact form submission from landing page."""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} – {self.submitted_at:%Y-%m-%d %H:%M}"
