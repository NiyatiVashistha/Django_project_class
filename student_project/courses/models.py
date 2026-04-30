from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from courses.utils import generate_unique_slug


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Course(models.Model):
    class DifficultyLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    difficulty = models.CharField(
        max_length=20,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.BEGINNER,
    )
    is_published = models.BooleanField(default=False)
    thumbnail = models.ImageField(
        upload_to="course_thumbnails/",
        blank=True,
        null=True,
    )

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses_taught",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["is_published"]),
            models.Index(fields=["difficulty"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_free(self):
        return self.price == Decimal("0.00")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Course, self.title)
        super().save(*args, **kwargs)


class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    video_url = models.URLField(blank=True, null=True, help_text="YouTube or Vimeo URL")
    video_file = models.FileField(upload_to="lesson_videos/", blank=True, null=True)
    notes_file = models.FileField(upload_to="lesson_notes/", blank=True, null=True)
    order = models.PositiveIntegerField(default=1)
    duration_minutes = models.PositiveIntegerField(default=0)
    is_preview = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["course", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "order"],
                name="unique_lesson_order_per_course",
            )
        ]

    def __str__(self):
        return f"{self.course.title} - Lesson {self.order}: {self.title}"


class Quiz(models.Model):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name="quiz")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    passing_score = models.PositiveIntegerField(default=70)

    def __str__(self):
        return f"Quiz: {self.title} ({self.lesson.title})"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class QuizAttempt(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.PositiveIntegerField()
    passed = models.BooleanField()
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title} ({self.score}%)"


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    enrolled_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-enrolled_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_enrollment_per_student_course",
            )
        ]

    def __str__(self):
        return f"{self.student.username} -> {self.course.title} [{self.status}]"

    @property
    def is_expired(self):
        """Enrollment validity is strictly 90 days. Forces repurchase."""
        if self.enrolled_at:
            return timezone.now() > self.enrolled_at + timedelta(days=90)
        return False

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="payment",
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    gateway = models.CharField(max_length=50, blank=True, default="")
    gateway_order_id = models.CharField(max_length=255, blank=True, default="")
    gateway_payment_id = models.CharField(max_length=255, blank=True, default="")
    gateway_signature = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment#{self.pk} - {self.enrollment.course.title} [{self.status}]"

    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED

    def complete(self, payment_id="", signature="", gateway="stripe"):
        self.status = self.Status.COMPLETED
        self.paid_at = timezone.now()
        self.gateway = gateway
        self.gateway_payment_id = payment_id
        self.gateway_signature = signature
        self.save(update_fields=[
            "status",
            "paid_at",
            "gateway",
            "gateway_payment_id",
            "gateway_signature",
        ])