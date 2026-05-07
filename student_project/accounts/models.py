"""
DATABASE MODELS: THE FOUNDATION OF IDENTITY
==========================================
In a web application, 'Models' are the blueprints for your data. 
This file defines who a 'User' is in our system and how we verify them.

KEY CONCEPTS:
1. CUSTOM USER MODEL: We extend Django's default User to add roles (Student/Instructor).
2. ROLE-BASED ACCESS (RBAC): We use a 'role' field to decide what a user can see.
3. OTP (One-Time Password): A security layer to verify email addresses.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import random
from datetime import timedelta

class UserManager(BaseUserManager):
    """
    THE USER MANAGER: The 'Factory' for Users.
    Django uses this class to handle the creation of users and superusers.
    It's where we define the rules for setting up a new account.
    """
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        user = self.model(
            username=username,
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True")

        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    THE USER MODEL: The 'Core' of the identity system.
    This class represents a row in our 'accounts_user' database table.
    """

    class Role(models.TextChoices):
        """
        ENUMERATION (Choices): Instead of typing 'student' everywhere, 
        we use these constants to avoid typos and keep data consistent.
        """
        STUDENT = "student", "Student"
        INSTRUCTOR = "instructor", "Instructor"
        ADMIN = "admin", "Admin"

    # DATABASE FIELDS: These are the columns in your database.
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)

    # ROLE FIELD: Decides if this user is a Student or an Instructor.
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT
    )

    is_active = models.BooleanField(default=True) # Used for OTP: accounts start inactive.
    is_staff = models.BooleanField(default=False) # Allows access to the Django Admin panel.

    bio = models.TextField(blank=True, null=True, help_text="Public profile bio for instructors.")
    profile_pic = models.ImageField(upload_to="instructor_profiles/", blank=True, null=True)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login_time = models.DateTimeField(null=True, blank=True)

    objects = UserManager() # Links this model to the manager factory defined above.

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username

    def record_login(self):
        """A helper method to track when users last accessed the platform."""
        self.last_login_time = timezone.now()
        self.save(update_fields=["last_login_time"])

    # PROPERTIES: These are like 'shortcuts' to check the user's role.
    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR


class OTPVerification(models.Model):
    """
    SECURITY FEATURE: One-Time Password (OTP)
    This model stores a secret code sent to a user's email.
    The user is only 'Activated' after they provide this code.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='otp_verification')
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def generate_otp(self):
        """Creates a random 6-digit number and resets the timer."""
        self.otp_code = str(random.randint(100000, 999999))
        self.created_at = timezone.now()
        self.is_verified = False
        self.save()

    def is_valid(self):
        """Check if the OTP was created within the last 10 minutes."""
        return timezone.now() < self.created_at + timedelta(minutes=10) and not self.is_verified


class Follow(models.Model):
    """
    SOCIAL FEATURE: Follow System
    Allows students to follow instructors to get updates on new courses.
    """
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following")
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "instructor") # Prevent duplicate follows

    def __str__(self):
        return f"{self.student.username} follows {self.instructor.username}"


class Student(User):
    """
    PROXY MODEL: Student
    A 'Virtual' model that points to the User table but acts as a filtered view.
    Used for creating a dedicated 'Students' section in the Admin panel.
    """
    class Meta:
        proxy = True
        verbose_name = "Student"
        verbose_name_plural = "Students"

    objects = UserManager() # Use the same manager

    def save(self, *args, **kwargs):
        self.role = User.Role.STUDENT
        super().save(*args, **kwargs)


class Instructor(User):
    """
    PROXY MODEL: Instructor
    A 'Virtual' model that points to the User table but acts as a filtered view.
    Used for creating a dedicated 'Instructors' section in the Admin panel.
    """
    class Meta:
        proxy = True
        verbose_name = "Instructor"
        verbose_name_plural = "Instructors"

    objects = UserManager() # Use the same manager

    def save(self, *args, **kwargs):
        self.role = User.Role.INSTRUCTOR
        super().save(*args, **kwargs)