from django.contrib import admin
from .models import Plan, UserProfile, ContactMessage


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_monthly', 'max_devices', 'max_children', 'is_active')
    list_filter = ('is_active',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'plan', 'children_count', 'signed_up_at')
    list_filter = ('plan', 'signed_up_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'phone_number')
    date_hierarchy = 'signed_up_at'


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'submitted_at', 'is_read')
    list_filter = ('is_read', 'submitted_at')
    search_fields = ('name', 'email', 'message')
    date_hierarchy = 'submitted_at'


admin.site.site_header = 'Guardian Agent Admin'
admin.site.site_title = 'Guardian Agent'
admin.site.index_title = 'Dashboard'
