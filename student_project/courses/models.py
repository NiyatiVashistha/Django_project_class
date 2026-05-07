"""
COURSE ARCHITECTURE: THE CONTENT LADDER
=======================================
This file defines how courses are structured. 
Think of it as a hierarchy:
Course (The Subject) -> Lesson (The Chapters) -> Enrollment (The Student Access)

KEY CONCEPTS:
1. FOREIGN KEYS: Linking one piece of data to another (e.g., Lesson belongs to Course).
2. SLUGS: Human-readable URLs (python-for-beginners) for better SEO.
3. CHOICES: Keeping data clean with predefined statuses (Draft, Published).
"""

from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from courses.utils import generate_unique_slug


class Category(models.Model):
    """
    CLASSIFICATION: Groups courses by topic (e.g., 'Programming', 'Design').
    Supports hierarchical sub-categories (e.g., IT -> Java).
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children'
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Course(models.Model):
    """
    THE COURSE: The primary unit of learning.
    It contains multiple lessons and belongs to an instructor.
    """
    class DifficultyLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    title = models.CharField(max_length=255)
    # SLUG: Used for 'slug-based' URLs like /courses/mastering-django/
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

    # FOREIGN KEYS: Relationships between different tables.
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
        """A convenience property to check if a course costs money."""
        return self.price == Decimal("0.00")

    def save(self, *args, **kwargs):
        """
        CUSTOM SAVE METHOD:
        Every time a course is saved, we check if it has a 'slug'.
        If not, we automatically generate one from the title.
        """
        if not self.slug:
            self.slug = generate_unique_slug(Course, self.title)
        super().save(*args, **kwargs)

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return sum([r.rating for r in reviews]) / len(reviews)


class Lesson(models.Model):
    """
    THE LESSON: A single chapter or video within a course.
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE, # If the course is deleted, its lessons are also deleted.
        related_name="lessons",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    video_url = models.URLField(blank=True, null=True, help_text="YouTube or Vimeo URL")
    video_file = models.FileField(upload_to="lesson_videos/", blank=True, null=True)
    notes_file = models.FileField(upload_to="lesson_notes/", blank=True, null=True)
    order = models.PositiveIntegerField(default=1) # Used to sequence chapters (1, 2, 3...)
    duration_minutes = models.PositiveIntegerField(default=0)
    is_preview = models.BooleanField(default=False) # Allows students to watch for free.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["course", "order"]
        constraints = [
            # Prevents two lessons from having the same order number in one course.
            models.UniqueConstraint(
                fields=["course", "order"],
                name="unique_lesson_order_per_course",
            )
        ]

    def __str__(self):
        return f"{self.course.title} - Lesson {self.order}: {self.title}"

    def get_embed_url(self):
        if not self.video_url:
            return ""
        if "youtube.com/watch?v=" in self.video_url:
            return self.video_url.replace("watch?v=", "embed/")
        if "youtu.be/" in self.video_url:
            return self.video_url.replace("youtu.be/", "youtube.com/embed/")
        return self.video_url


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
    """
    ACCESS CONTROL: The link between a Student and a Course.
    If this record exists, the student can access the course content.
    """
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
            # A student can only enroll in a specific course ONCE.
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_enrollment_per_student_course",
            )
        ]

    def __str__(self):
        return f"{self.student.username} -> {self.course.title} [{self.status}]"

    @property
    def is_expired(self):
        """
        BUSINESS LOGIC: 90-Day Expiry.
        We check if the current date is 90 days past the enrollment date.
        """
        if self.enrolled_at:
            return timezone.now() > self.enrolled_at + timedelta(days=90)
        return False

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])


class Payment(models.Model):
    """
    FINANCIALS: Tracks money paid for courses.
    Linked 1-to-1 with an Enrollment.
    """
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

    # EXTERNAL DATA: Storing details from the payment gateway (e.g., Stripe).
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
        """A helper method to finalize a payment once verified by the gateway."""
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


class SiteConfiguration(models.Model):
    """
    DYNAMIC LAYOUT: Allows Admins to change the website look without touching code.
    This follows the 'Singleton' pattern (only one record should exist).
    """
    site_name = models.CharField(max_length=100, default="Academic LMS")
    site_logo = models.ImageField(upload_to="site/", blank=True, null=True)
    hero_image = models.ImageField(upload_to="site/", blank=True, null=True)
    
    # Theme Colors
    primary_color = models.CharField(max_length=7, default="#1a73e8", help_text="HEX Color for primary elements")
    secondary_color = models.CharField(max_length=7, default="#202124", help_text="HEX Color for secondary elements")
    
    # Hero Section
    hero_title = models.CharField(max_length=255, default="Learn Without Limits")
    hero_subtitle = models.TextField(default="Start, switch, or advance your career with world-class online courses.")
    
    # Layout Toggle
    LAYOUT_CHOICES = [
        ('modern', 'Modern (Sidebar)'),
        ('classic', 'Classic (Top Navbar)'),
    ]
    layout_type = models.CharField(max_length=20, choices=LAYOUT_CHOICES, default='classic')
    
    # Announcements & Offers
    announcement_text = models.CharField(max_length=255, blank=True, null=True, help_text="Top bar announcement (e.g., 'Maintenance at 10 PM')")
    show_announcement = models.BooleanField(default=False)
    
    offer_text = models.CharField(max_length=255, blank=True, null=True, help_text="Promotional offer (e.g., '50% Off on all Python courses!')")
    offer_link = models.CharField(max_length=200, blank=True, null=True, help_text="URL for the offer")
    show_offer = models.BooleanField(default=False)
    
    # Commercial & Social Links
    facebook_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    office_address = models.TextField(blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configurations"

    def __str__(self):
        return f"Configuration updated at {self.updated_at}"

    def save(self, *args, **kwargs):
        """Ensure only one instance exists (Singleton)."""
        if not self.pk and SiteConfiguration.objects.exists():
            return # Prevent creation of multiple configs
        super().save(*args, **kwargs)


class ChatLog(models.Model):
    """
    Records interactions with the Academic Assistant.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat by {self.user or 'Guest'} at {self.timestamp}"


class ContactMessage(models.Model):
    """
    Stores messages sent via the Contact Form.
    """
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"

    class Meta:
        ordering = ["-created_at"]


class Community(models.Model):
    """
    SOCIAL FEATURE: Communities
    Groups where students and instructors can interact.
    Each course can have its own dedicated community.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField()
    thumbnail = models.ImageField(upload_to="community_thumbs/", blank=True, null=True)
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name="community", null=True, blank=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_communities")
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="communities", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from courses.utils import generate_unique_slug
            self.slug = generate_unique_slug(Community, self.name)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Communities"


class CommunityMessage(models.Model):
    """
    CHAT FEATURE: Messages within a community.
    """
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.user.username}: {self.content[:20]}"


class Review(models.Model):
    """
    FEEDBACK FEATURE: Student reviews for courses.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="reviews")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "student") # One review per student per course

    def __str__(self):
        return f"{self.student.username} - {self.course.title} ({self.rating}*)"


class CategoryRequest(models.Model):
    """
    WORKFLOW FEATURE: Instructor requests for new categories.
    Admins must approve these before they can be used.
    """
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request: {self.name} by {self.instructor.username}"


class MailDraft(models.Model):
    """
    ADMIN FEATURE: Mail Drafting
    Allows admins to draft and send emails to users.
    """
    subject = models.CharField(max_length=200)
    body = models.TextField()
    recipient_type = models.CharField(
        max_length=20,
        choices=[('all', 'All Users'), ('students', 'Students Only'), ('instructors', 'Instructors Only')],
        default='all'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.subject


class LessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress_records")
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}"