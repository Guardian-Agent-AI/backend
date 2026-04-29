from django.contrib import admin
from .models import Plan, UserProfile, ContactMessage, Child, Device, ChatMessage, GameSession, AlertEvent


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_monthly', 'max_devices', 'is_active')
    list_filter = ('is_active',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'plan', 'signed_up_at')
    list_filter = ('plan', 'signed_up_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'phone_number')
    date_hierarchy = 'signed_up_at'


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'age', 'created_at')
    search_fields = ('name',)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'profile', 'child', 'device_type', 'is_active', 'last_seen')
    list_filter = ('device_type', 'is_active')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('speaker', 'game_name', 'message_type', 'is_flagged', 'timestamp')
    list_filter = ('message_type', 'is_flagged', 'game_name')
    date_hierarchy = 'timestamp'


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ('child', 'game_name', 'started_at', 'ended_at')
    date_hierarchy = 'started_at'


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = ('child', 'game_name', 'category', 'timestamp', 'is_read')
    list_filter = ('category', 'is_read')
    date_hierarchy = 'timestamp'


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'submitted_at', 'is_read')
    list_filter = ('is_read', 'submitted_at')
    search_fields = ('name', 'email', 'message')
    date_hierarchy = 'submitted_at'


admin.site.site_header = 'Guardian Agent Admin'
admin.site.site_title = 'Guardian Agent'
admin.site.index_title = 'Dashboard'
