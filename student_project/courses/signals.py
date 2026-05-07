from django.db.models.signals import post_save
from django.dispatch import receiver
from courses.models import Course, Enrollment, Community

@receiver(post_save, sender=Course)
def create_course_community(sender, instance, created, **kwargs):
    """
    Automatically create a community for every new course.
    """
    if created:
        Community.objects.get_or_create(
            course=instance,
            defaults={
                'name': f"{instance.title} Community",
                'creator': instance.instructor or instance.instructor.objects.filter(role='admin').first(),
                'description': f"Join the discussion for {instance.title}!"
            }
        )

@receiver(post_save, sender=Enrollment)
def join_community_on_enrollment(sender, instance, created, **kwargs):
    """
    Automatically add students to the course community when they enroll.
    """
    if created:
        course = instance.course
        community = getattr(course, 'community', None)
        if community:
            community.members.add(instance.student)