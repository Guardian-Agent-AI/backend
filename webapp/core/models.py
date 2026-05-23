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
    description = models.TextField(blank=True)
    features = models.TextField(blank=True, help_text="One feature per line")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    stripe_product_id = models.CharField(max_length=100, blank=True, default='')
    stripe_price_id = models.CharField(max_length=100, blank=True, default='', db_index=True)

    def feature_list(self):
        return [f.strip() for f in self.features.splitlines() if f.strip()]

    def __str__(self):
        return f"{self.name} – €{self.price_monthly}/mo"


class UserProfile(models.Model):
    """Extended profile linked to Django User – stores phone, plan, etc."""
    SUB_STATUS_NONE       = 'none'
    SUB_STATUS_ACTIVE     = 'active'
    SUB_STATUS_PAST_DUE   = 'past_due'
    SUB_STATUS_CANCELING  = 'canceling'  # cancels at period end
    SUB_STATUS_CANCELED   = 'canceled'
    SUB_STATUS_CHOICES = [
        (SUB_STATUS_NONE,      'No subscription'),
        (SUB_STATUS_ACTIVE,    'Active'),
        (SUB_STATUS_PAST_DUE,  'Past due'),
        (SUB_STATUS_CANCELING, 'Cancels at period end'),
        (SUB_STATUS_CANCELED,  'Canceled'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=17, validators=[phone_validator], blank=True, default='')
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    children_count = models.PositiveIntegerField(default=1)
    signed_up_at = models.DateTimeField(default=timezone.now)

    # Stripe linkage
    stripe_customer_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    subscription_status = models.CharField(max_length=20, choices=SUB_STATUS_CHOICES, default=SUB_STATUS_NONE)
    current_period_end = models.DateTimeField(null=True, blank=True)

    @property
    def has_active_subscription(self):
        return self.subscription_status in (self.SUB_STATUS_ACTIVE, self.SUB_STATUS_CANCELING)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.email})"


class Child(models.Model):
    """A child being monitored, linked to a parent's UserProfile."""
    parent = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='children')
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (parent: {self.parent})"


class GameSession(models.Model):
    """A single detected gaming session for a child."""
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='sessions')
    device = models.ForeignKey('Device', on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    game_name = models.CharField(max_length=200)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)

    @property
    def duration_minutes(self):
        if self.ended_at:
            return max(0, int((self.ended_at - self.started_at).total_seconds() / 60))
        return 0

    def __str__(self):
        return f"{self.child.name} – {self.game_name} @ {self.started_at:%Y-%m-%d %H:%M}"


class AlertEvent(models.Model):
    """A flagged incident detected during a child's gaming session."""
    CATEGORY_CHOICES = [
        ('meeting_request',          'Meeting Request'),
        ('personal_info_request',    'Personal Info Request'),
        ('social_media_solicitation','Social Media Solicitation'),
        ('photo_video_request',      'Photo/Video Request'),
        ('grooming_language',        'Grooming Language'),
        ('secrecy_request',          'Secrecy Request'),
        ('threats_bullying',         'Threats / Bullying'),
        ('gift_bribery',             'Gift / Bribery'),
        ('other',                    'Other'),
    ]
    # badge colour (Bootstrap), icon (FA), label
    CATEGORY_META = {
        'meeting_request':           ('danger',    'fa-map-marker-alt',     'Meeting Request'),
        'personal_info_request':     ('warning',   'fa-id-card',            'Personal Info'),
        'social_media_solicitation': ('info',      'fa-share-alt',          'Social Media'),
        'photo_video_request':       ('danger',    'fa-camera',             'Photo/Video'),
        'grooming_language':         ('danger',    'fa-exclamation-triangle','Grooming Language'),
        'secrecy_request':           ('warning',   'fa-user-secret',        'Secrecy Request'),
        'threats_bullying':          ('dark',      'fa-fist-raised',        'Threats/Bullying'),
        'gift_bribery':              ('secondary', 'fa-gift',               'Gift/Bribery'),
        'other':                     ('secondary', 'fa-question-circle',    'Other'),
    }

    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='alerts')
    game_name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    category_label = models.CharField(max_length=200, blank=True)
    sms_message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    @property
    def badge_class(self):
        return self.CATEGORY_META.get(self.category, ('secondary', '', ''))[0]

    @property
    def icon(self):
        return self.CATEGORY_META.get(self.category, ('', 'fa-question-circle', ''))[1]

    @property
    def display_category(self):
        if self.category == 'other' and self.category_label:
            return self.category_label
        return self.CATEGORY_META.get(self.category, ('', '', self.get_category_display()))[2]

    def __str__(self):
        return f"{self.child.name} – {self.display_category} @ {self.timestamp:%Y-%m-%d %H:%M}"


class CommunityThreatStat(models.Model):
    """System-wide count of each threat category detected this week across all users."""
    category = models.CharField(max_length=50, choices=AlertEvent.CATEGORY_CHOICES, unique=True)
    count = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-count']

    @property
    def display_label(self):
        return AlertEvent.CATEGORY_META.get(self.category, ('', '', self.get_category_display()))[2]

    @property
    def icon(self):
        return AlertEvent.CATEGORY_META.get(self.category, ('', 'fa-question-circle', ''))[1]

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

class Device(models.Model):
    """A device (PC, console, etc.) with Guardian Agent installed."""
    DEVICE_TYPES = [
        ('pc', 'PC'),
        ('console', 'Console'),
        ('mobile', 'Mobile'),
        ('other', 'Other'),
    ]
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='devices')
    child = models.ForeignKey(Child, on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')
    name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, default='pc')
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_device_type_display()})"


class ChatMessage(models.Model):
    """A chat message captured on a monitored device."""
    MESSAGE_TYPES = [
        ('voice', 'Voice'),
        ('text', 'Text'),
    ]
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='messages')
    game_name = models.CharField(max_length=200)
    speaker = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    is_flagged = models.BooleanField(default=False)
    alert = models.ForeignKey(AlertEvent, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.speaker}: {self.content[:50]} ({self.game_name})"

class ContactMessage(models.Model):
    """Contact form submission from landing page."""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} – {self.submitted_at:%Y-%m-%d %H:%M}"
