from django.urls import path
from . import views
from . import api

urlpatterns = [
    path('', views.landing, name='landing'),
    path('signup/', views.signup_view, name='signup_no_plan'),
    path('signup/<int:plan_id>/', views.signup_view, name='signup'),
    path('signin/', views.signin_view, name='signin'),
    path('signout/', views.signout_view, name='signout'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/plan/<int:plan_id>/', views.choose_plan, name='choose_plan'),
    path('install/', views.install_page, name='install'),
    path('download/<str:platform>/', views.download_app, name='download_app'),

    # REST API (for desktop app)
    path('api/auth/login/', api.api_login, name='api_login'),
    path('api/auth/me/', api.api_me, name='api_me'),
    path('api/plans/', api.api_plans, name='api_plans'),
]
