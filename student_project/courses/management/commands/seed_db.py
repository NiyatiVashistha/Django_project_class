from django.core.management.base import BaseCommand
from accounts.models import User
from courses.models import Course, Category, Lesson
from django.utils import timezone
from decimal import Decimal

class Command(BaseCommand):
    help = "Seeds the database with an educator and specific technical courses."

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting database seeding...")

        # 1. Create Educator
        educator, created = User.objects.get_or_create(
            username="educator",
            email="educator@lms.com",
            defaults={"role": User.Role.INSTRUCTOR, "is_active": True}
        )
        if created:
            educator.set_password("educator123")
            educator.save()

        # 2. Categories
        cat_dev, _ = Category.objects.get_or_create(name="Software Development", slug="software-development")
        cat_data, _ = Category.objects.get_or_create(name="Data & Analytics", slug="data-analytics")

        # 3. Create Specific Tech Courses
        courses_data = [
            {
                "title": "Django Masterclass",
                "description": "Learn rapid Web Development with Python's most powerful framework.",
                "price": Decimal("19.99"),
                "difficulty": Course.DifficultyLevel.INTERMEDIATE,
                "category": cat_dev,
            },
            {
                "title": "Java Enterprise Server",
                "description": "Build massive backend architectures with Java EE.",
                "price": Decimal("59.99"),
                "difficulty": Course.DifficultyLevel.ADVANCED,
                "category": cat_dev,
            },
            {
                "title": "SpringBoot APIs",
                "description": "Create incredibly scalable microservice architectures using SpringBoot.",
                "price": Decimal("29.99"),
                "difficulty": Course.DifficultyLevel.ADVANCED,
                "category": cat_dev,
            },
            {
                "title": "NodeJS Backend Systems",
                "description": "JavaScript on the server. Write efficient event-driven APIs.",
                "price": Decimal("0.00"),
                "difficulty": Course.DifficultyLevel.BEGINNER,
                "category": cat_dev,
            },
            {
                "title": "Data Science Fundamentals",
                "description": "Learn Pandas, scikit-learn, and mathematical models to extract insights.",
                "price": Decimal("12.50"),
                "difficulty": Course.DifficultyLevel.INTERMEDIATE,
                "category": cat_data,
            },
            {
                "title": "Data Engineering Pipelines",
                "description": "Design massive ETL systems using Apache Airflow, Kafka, and Snowflake.",
                "price": Decimal("99.99"),
                "difficulty": Course.DifficultyLevel.ADVANCED,
                "category": cat_data,
            }
        ]

        Course.objects.filter(instructor=educator).delete()
        
        for data in courses_data:
            course = Course.objects.create(instructor=educator, is_published=True, **data)
            Lesson.objects.create(
                course=course, title="Orientation", content=f"Welcome to {course.title}. Let's begin.", order=1, duration_minutes=15
            )
            self.stdout.write(self.style.SUCCESS(f'Created Built-in Course: {course.title}'))

        self.stdout.write(self.style.SUCCESS('Seeded all requested courses successfully!'))
