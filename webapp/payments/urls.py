from django.urls import path
from . import views

urlpatterns = [
    path('checkout/<int:plan_id>/', views.create_checkout_session, name='create_checkout_session'),
    path('success/', views.payment_success, name='payment_success'),
    path('cancel/', views.payment_cancel, name='payment_cancel'),
    path('webhooks/stripe/', views.stripe_webhook, name='stripe_webhook'),
]
