from decimal import Decimal

import stripe
from django.conf import settings
from django.db import IntegrityError, transaction
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q
from django.urls import reverse
from django.utils import timezone

from accounts.mongo import log_search, log_activity, log_payment
from courses.models import Course, Enrollment, Payment


def search_courses(query, sort_by=None, category_id=None, user=None, page=1, per_page=9):
    queryset = Course.objects.filter(is_published=True).select_related(
        "instructor", "category"
    ).annotate(enrollment_count=Count("enrollments"))

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

    if category_id:
        queryset = queryset.filter(category_id=category_id)

    if sort_by == 'popular':
        queryset = queryset.order_by('-enrollment_count', '-created_at')
    elif sort_by == 'free':
        queryset = queryset.filter(price=0).order_by('-created_at')
    elif sort_by == 'created_at':
        queryset = queryset.order_by('created_at')
    elif sort_by == 'newest':
        queryset = queryset.order_by('-created_at')
    else:
        # Default: newest first
        queryset = queryset.order_by('-created_at')

    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)
    return page_obj, paginator


def is_enrolled(student, course):
    enrollments = Enrollment.objects.filter(
        student=student,
        course=course,
        status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED],
    )
    # If they hold an enrollment but it's expired, they are NOT enrolled.
    for e in enrollments:
        if not e.is_expired:
            return True
    return False


@transaction.atomic
def enroll_student(student, course):
    # EXPIRY REPURCHASING MECHANIC
    # Cleanse any expired enrollments so the unique constraint drops and they can buy again.
    expired = Enrollment.objects.filter(student=student, course=course)
    for e in expired:
        if e.is_expired:
            e.delete()

    try:
        enrollment, created = Enrollment.objects.get_or_create(
            student=student,
            course=course,
            defaults={"status": Enrollment.Status.ACTIVE},
        )
        return enrollment, created
    except IntegrityError:
        enrollment = Enrollment.objects.get(student=student, course=course)
        return enrollment, False


@transaction.atomic
def create_stripe_checkout_session(request, enrollment):
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
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.retrieve(session_id)

    if session.payment_status != "paid":
        return None

    payment = Payment.objects.get(gateway_order_id=session_id)

    if payment.is_completed:
        return payment

    payment.status = Payment.Status.COMPLETED
    payment.paid_at = timezone.now()
    payment.gateway_payment_id = session.get("payment_intent") or ""
    payment.gateway_signature = "verified_by_stripe"
    payment.save(update_fields=[
        "status",
        "paid_at",
        "gateway_payment_id",
        "gateway_signature",
    ])

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
    log_activity(user_id, path, meta or {})