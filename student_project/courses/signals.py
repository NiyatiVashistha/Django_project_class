from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Course


@receiver(post_save, sender=Course)
def course_saved(sender, instance, created, **kwargs):
    pass