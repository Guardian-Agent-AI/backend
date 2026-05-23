from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'description', 'amount_display', 'currency', 'status', 'created_at')
    list_filter = ('status', 'currency')
    search_fields = ('user__email', 'description', 'stripe_payment_intent_id')
    readonly_fields = ('stripe_checkout_session_id', 'stripe_payment_intent_id', 'created_at', 'updated_at')
