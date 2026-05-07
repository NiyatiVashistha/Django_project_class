from decimal import Decimal

import stripe
from django.conf import settings
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Sum, Q
from django.urls import reverse
from django.utils import timezone

from accounts.mongo import log_search, log_activity, log_payment
from courses.models import Course, Enrollment, Payment


def search_courses(query, user=None, page=1, per_page=9, sort_by="", category_id=None):
    queryset = Course.objects.filter(is_published=True).select_related(
        "instructor", "category"
    ).annotate(enrollment_count=Count("enrollments"))

    if category_id:
        queryset = queryset.filter(category_id=category_id)

    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(instructor__username__icontains=query)
        )

        if user and user.is_authenticated:
            try:
                log_search(user.id, query, queryset.count())
            except Exception:
                pass

    if sort_by == "price_low":
        queryset = queryset.order_by("price")
    elif sort_by == "price_high":
        queryset = queryset.order_by("-price")
    elif sort_by == "newest":
        queryset = queryset.order_by("-created_at")
    elif sort_by == "popular":
        queryset = queryset.order_by("-enrollment_count")
    else:
        queryset = queryset.order_by("-created_at")

    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)
    return page_obj, paginator


def is_enrolled(student, course):
    return Enrollment.objects.filter(
        student=student,
        course=course,
        status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED],
    ).exists()


@transaction.atomic
def enroll_student(student, course):
    try:
        enrollment, created = Enrollment.objects.get_or_create(
            student=student,
            course=course,
            defaults={"status": Enrollment.Status.ACTIVE},
        )
        return enrollment, created
    except IntegrityError:
        enrollment = Enrollment.objects.select_for_update().get(student=student, course=course)
        return enrollment, False


@transaction.atomic
def create_stripe_checkout_session(request, enrollment):
    if settings.STRIPE_MOCK_MODE:
        # Simulate a successful checkout session creation
        payment, _ = Payment.objects.get_or_create(
            enrollment=enrollment,
            defaults={
                "amount": enrollment.course.price,
                "status": Payment.Status.PENDING,
                "gateway": "mock",
                "gateway_order_id": f"mock_{timezone.now().timestamp()}",
            },
        )
        # Mock session object with a redirect URL back to success
        class MockSession:
            def __init__(self, url):
                self.url = url
                self.id = f"mock_{timezone.now().timestamp()}"
                self.payment_status = "paid"
            def get(self, key, default=None):
                return getattr(self, key, default)
        
        success_url = request.build_absolute_uri(
            reverse("courses:payment_success", kwargs={"slug": enrollment.course.slug})
        ) + f"?session_id={payment.gateway_order_id}"
        
        return MockSession(success_url), payment

    stripe.api_key = settings.STRIPE_SECRET_KEY

    amount_in_paise = int(enrollment.course.price * 100)

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY,
                    "product_data": {
                        "name": enrollment.course.title,
                    },
                    "unit_amount": amount_in_paise,
                },
                "quantity": 1,
            }
        ],
        success_url=request.build_absolute_uri(
            reverse("courses:payment_success", kwargs={"slug": enrollment.course.slug})
        ) + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri(
            reverse("courses:payment", kwargs={"slug": enrollment.course.slug})
        ),
        metadata={
            "enrollment_id": str(enrollment.id),
            "course_id": str(enrollment.course.id),
            "student_id": str(enrollment.student.id),
        },
    )

    payment, _ = Payment.objects.get_or_create(
        enrollment=enrollment,
        defaults={
            "amount": enrollment.course.price,
            "status": Payment.Status.PENDING,
            "gateway": "stripe",
            "gateway_order_id": session.id,
        },
    )

    if payment.gateway_order_id != session.id:
        payment.gateway = "stripe"
        payment.gateway_order_id = session.id
        payment.save(update_fields=["gateway", "gateway_order_id"])

    return session, payment


@transaction.atomic
def finalize_stripe_payment(session_id):
    if session_id.startswith("mock_"):
        payment = Payment.objects.select_for_update().get(gateway_order_id=session_id)
        if payment.status == Payment.Status.COMPLETED:
            return payment
        payment.status = Payment.Status.COMPLETED
        payment.paid_at = timezone.now()
        payment.save()
        
        # Trigger email even in mock for testing
        send_payment_confirmation_email(payment)
        
        return payment

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.retrieve(session_id)

    if session.payment_status != "paid":
        return None

    payment = Payment.objects.select_for_update().get(gateway_order_id=session_id)

    if payment.status == Payment.Status.COMPLETED:
        return payment

    payment.status = Payment.Status.COMPLETED
    payment.paid_at = timezone.now()
    # Use getattr to safely access attributes that might not exist or might not support .get()
    payment.gateway_payment_id = getattr(session, "payment_intent", "") or ""
    payment.gateway_signature = "verified_by_stripe"
    payment.save(update_fields=[
        "status",
        "paid_at",
        "gateway_payment_id",
        "gateway_signature",
    ])

    # Send Confirmation Email
    send_payment_confirmation_email(payment)

    try:
        log_payment(
            user_id=payment.enrollment.student.id,
            course_id=payment.enrollment.course.id,
            amount=float(payment.amount),
            status="completed",
        )
    except Exception:
        pass

    return payment


def send_payment_confirmation_email(payment):
    """
    Sends a professional email to the student upon successful course purchase.
    """
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    
    student = payment.enrollment.student
    course = payment.enrollment.course
    
    subject = f"Payment Confirmed: Welcome to {course.title}!"
    message = f"""
    Hi {student.username},

    Thank you for your payment of ₹{payment.amount}. 
    Your enrollment in "{course.title}" is now confirmed!

    You can start learning right away by clicking the link below:
    http://127.0.0.1:8000/courses/course/{course.slug}/learn/

    Happy Learning,
    The Academic Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [student.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Failed to send email: {e}")


def get_student_dashboard_data(student):
    enrollments = Enrollment.objects.filter(student=student).select_related(
        "course", "course__instructor", "course__category"
    ).prefetch_related("payment")

    total_spent = Payment.objects.filter(
        enrollment__student=student,
        status=Payment.Status.COMPLETED,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    status_counts = Enrollment.objects.filter(student=student).values("status").annotate(
        count=Count("id")
    )

    return {
        "enrollments": enrollments,
        "total_spent": total_spent,
        "status_counts": {row["status"]: row["count"] for row in status_counts},
        "enrollment_count": enrollments.count(),
    }


def log_course_activity(user_id, path, meta=None):
    try:
        log_activity(user_id, path, meta or {})
    except Exception:
        pass


def get_admin_analytics_data():
    """
    ADMIN ANALYTICS: Aggregates platform-wide data.
    """
    from accounts.models import User
    
    total_revenue = Payment.objects.filter(
        status=Payment.Status.COMPLETED
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    
    total_students = User.objects.filter(role=User.Role.STUDENT).count()
    total_courses = Course.objects.count()
    
    # NEW: Advanced Analysis Metrics
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    student_growth = User.objects.filter(role=User.Role.STUDENT, date_joined__gte=thirty_days_ago).count()
    
    seven_days_ago = timezone.now() - timezone.timedelta(days=7)
    recent_revenue = Payment.objects.filter(
        status=Payment.Status.COMPLETED,
        paid_at__gte=seven_days_ago
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    
    # Category-wise enrollment distribution
    from courses.models import Category
    category_data = Category.objects.annotate(
        enrollment_count=Count('courses__enrollments')
    ).values('name', 'enrollment_count').order_by('-enrollment_count')
    
    # Recent Chat Logs for staff analysis
    try:
        from courses.models import ChatLog
        recent_chats = ChatLog.objects.select_related('user').order_by('-timestamp')[:10]
    except:
        recent_chats = []
    
    # Top 5 selling courses based on enrollment count
    top_courses = Course.objects.annotate(
        enrollments_count=Count('enrollments')
    ).order_by('-enrollments_count')[:5]
    
    recent_payments = Payment.objects.filter(
        status=Payment.Status.COMPLETED
    ).select_related("enrollment", "enrollment__student", "enrollment__course").order_by("-paid_at")[:10]
    
    return {
        "total_revenue": total_revenue,
        "total_students": total_students,
        "total_courses": total_courses,
        "student_growth": student_growth,
        "recent_revenue": recent_revenue,
        "category_data": category_data,
        "top_courses": top_courses,
        "recent_payments": recent_payments,
        "recent_chats": recent_chats,
    }