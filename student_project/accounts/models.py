from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import random
from datetime import timedelta

class UserManager(BaseUserManager):
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

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        INSTRUCTOR = "instructor", "Instructor"
        ADMIN = "admin", "Admin"

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    bio = models.TextField(blank=True, null=True, help_text="Public profile bio for instructors.")
    profile_pic = models.ImageField(upload_to="instructor_profiles/", blank=True, null=True)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login_time = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username

    def record_login(self):
        self.last_login_time = timezone.now()
        self.save(update_fields=["last_login_time"])

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR


class OTPVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='otp_verification')
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def generate_otp(self):
        self.otp_code = str(random.randint(100000, 999999))
        self.created_at = timezone.now()
        self.is_verified = False
        self.save()

    def is_valid(self):
        return timezone.now() < self.created_at + timedelta(minutes=10) and not self.is_verified