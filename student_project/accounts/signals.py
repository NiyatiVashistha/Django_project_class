from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User


@receiver(post_save, sender=User)
def user_created(sender, instance, created, **kwargs):
    if created:
        # placeholder for future automation, such as profile creation
        pass