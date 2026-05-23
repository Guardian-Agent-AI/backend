from django.contrib import admin
from .models import (
    Alert, Child, CommunityPeakTimeStat, CommunityThreatStat,
    ContactMessage, Device, GameSession, Incident, Plan, UserProfile, WeeklyReport,
)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_monthly', 'max_devices', 'max_children', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'plan', 'stripe_customer_id', 'signed_up_at', 'onboarded_at')
    list_filter = ('plan',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'phone_number', 'stripe_customer_id')
    date_hierarchy = 'signed_up_at'


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'age', 'date_of_birth', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'parent__user__email', 'parent__user__first_name')


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'child', 'device_type', 'os', 'agent_version', 'is_active', 'last_seen_at')
    list_filter = ('device_type', 'is_active')
    search_fields = ('name', 'child__name', 'os', 'agent_version')


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ('child', 'game_name', 'device', 'started_at', 'ended_at', 'duration_minutes')
    list_filter = ('game_name',)
    search_fields = ('child__name', 'game_name')
    date_hierarchy = 'started_at'

    @admin.display(description='Duration (min)')
    def duration_minutes(self, obj):
        return obj.duration_minutes


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('child', 'severity', 'category', 'game_name', 'detected_at', 'reviewed_by_parent', 'is_false_positive')
    list_filter = ('severity', 'category', 'reviewed_by_parent', 'is_false_positive')
    search_fields = ('child__name', 'game_name', 'summary')
    date_hierarchy = 'detected_at'
    readonly_fields = ('detected_at',)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('incident', 'alert_type', 'status', 'sent_at')
    list_filter = ('alert_type', 'status')
    search_fields = ('incident__child__name', 'message_preview')
    date_hierarchy = 'sent_at'


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'week_start', 'week_end', 'email_status', 'sent_at')
    list_filter = ('email_status',)
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    date_hierarchy = 'week_start'


@admin.register(CommunityThreatStat)
class CommunityThreatStatAdmin(admin.ModelAdmin):
    list_display = ('display_label', 'count', 'last_updated')
    ordering = ('-count',)


@admin.register(CommunityPeakTimeStat)
class CommunityPeakTimeStatAdmin(admin.ModelAdmin):
    list_display = ('label', 'hour_start', 'count', 'last_updated')
    ordering = ('hour_start',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'submitted_at', 'is_read')
    list_filter = ('is_read',)
    search_fields = ('name', 'email', 'message')
    date_hierarchy = 'submitted_at'


admin.site.site_header = 'Guardian Agent Admin'
admin.site.site_title = 'Guardian Agent'
admin.site.index_title = 'Dashboard'
