from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create a UserProfile for every new User (e.g. superusers)."""
    if created:
        try:
            UserProfile.objects.get_or_create(user=instance)
        except Exception:
            pass  # Don't block user creation if UserProfile table isn't ready
