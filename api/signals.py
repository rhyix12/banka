from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ActivityLog, User, Fisherfolk
from django.utils.timezone import now

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ActivityLog.objects.create(
        user=user,
        action=f"{user.username} logged in",
        timestamp=now()
    )

@receiver(post_save, sender=Fisherfolk)
def log_fisherfolk_created(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.created_by,  # This will now be set
            action=f"Fisherfolk {instance} was created",
        )