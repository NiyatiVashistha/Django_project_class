from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Category, Course, Enrollment

User = get_user_model()


class CourseFlowTest(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="pass12345",
        )
        self.category = Category.objects.create(name="Python", slug="python")
        self.course = Course.objects.create(
            title="Django Basics",
            slug="django-basics",
            description="Introductory Django course",
            price=Decimal("0.00"),
            is_published=True,
            category=self.category,
        )

    def test_course_list_page(self):
        response = self.client.get(reverse("courses:course_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django Basics")

    def test_course_detail_page(self):
        response = self.client.get(reverse("courses:course_detail", kwargs={"slug": self.course.slug}))
        self.assertEqual(response.status_code, 200)

    def test_enroll_requires_login(self):
        response = self.client.post(reverse("courses:enroll", kwargs={"slug": self.course.slug}))
        self.assertEqual(response.status_code, 302)