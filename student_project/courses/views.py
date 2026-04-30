import json
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from courses.models import Course, Enrollment, Lesson, Payment
from courses.services import (
    search_courses,
    enroll_student,
    is_enrolled,
    create_stripe_checkout_session,
    finalize_stripe_payment,
    get_student_dashboard_data,
    log_course_activity,
)


# ──────────────────────────────────────────────
# Decorators
# ──────────────────────────────────────────────

def instructor_required(view_func):
    """Allow only users whose role is 'instructor'."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not getattr(request.user, 'is_instructor', False):
            raise PermissionDenied("Only instructors can access this area.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    """Allow only users whose role is 'admin'."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or getattr(request.user, 'role', '') != 'admin':
            raise PermissionDenied("Only Administrators can access this area.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ──────────────────────────────────────────────
# Public Views
# ──────────────────────────────────────────────

def landing_view(request):
    from accounts.models import User
    from django.db.models import Count
    
    # New Courses (latest created)
    new_courses = Course.objects.filter(is_published=True).order_by("-created_at")[:4]
    
    # Popular Courses (most enrollments)
    popular_courses = Course.objects.filter(is_published=True).annotate(
        enroll_count=Count('enrollments')
    ).order_by('-enroll_count')[:4]
    
    # Trending Now (randomized/engagement based)
    trending_courses = Course.objects.filter(is_published=True).order_by('?')[:4]
    
    top_instructors = User.objects.filter(role=User.Role.INSTRUCTOR)[:4]
    
    return render(request, "landing.html", {
        "new_courses": new_courses,
        "popular_courses": popular_courses,
        "trending_courses": trending_courses,
        "top_instructors": top_instructors
    })


def course_list_view(request):
    from courses.forms import SearchForm

    form = SearchForm(request.GET or None)
    query = ""
    sort_by = ""
    category_id = None

    if form.is_valid():
        query = form.cleaned_data["q"]
        sort_by = form.cleaned_data.get("sort")
        category = form.cleaned_data.get("category")
        if category:
            category_id = category.id

    page_number = request.GET.get("page", 1)

    page_obj, paginator = search_courses(
        query=query,
        user=request.user,
        page=page_number,
        sort_by=sort_by,
        category_id=category_id,
    )

    return render(request, "courses/course_list.html", {
        "form": form,
        "query": query,
        "page_obj": page_obj,
        "paginator": paginator,
    })


def course_detail_view(request, slug):
    course = get_object_or_404(Course.objects.select_related("instructor", "category"), slug=slug)
    
    # Allow viewing if published OR if the user is the instructor
    if not course.is_published:
        if not request.user.is_authenticated or (course.instructor != request.user and request.user.role != 'admin'):
            messages.error(request, "This course is currently in draft mode.")
            return redirect("courses:course_list")

    lessons = course.lessons.all().order_by("order")
    enrolled = request.user.is_authenticated and is_enrolled(request.user, course)

    return render(request, "courses/course_detail.html", {
        "course": course,
        "lessons": lessons,
        "enrolled": enrolled,
    })


# ──────────────────────────────────────────────
# Enrollment & Payment Views
# ──────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def enroll_view(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    enrollment, created = enroll_student(request.user, course)

    if created:
        messages.success(request, "Enrollment successful.")
    else:
        messages.info(request, "Already enrolled.")

    return redirect("courses:learn" if course.is_free else "courses:payment", slug=slug)


@login_required
@require_http_methods(["GET", "POST"])
def payment_view(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)

    try:
        enrollment = Enrollment.objects.get(student=request.user, course=course)
    except Enrollment.DoesNotExist:
        messages.error(request, "Enroll first.")
        return redirect("courses:course_detail", slug=slug)

    payment, _ = Payment.objects.get_or_create(
        enrollment=enrollment,
        defaults={"amount": course.price, "status": Payment.Status.PENDING},
    )

    if payment.status == Payment.Status.COMPLETED:
        return redirect("courses:learn", slug=slug)

    if request.method == "POST":
        session, _ = create_stripe_checkout_session(request, enrollment)
        return redirect(session.url, permanent=False)

    return render(request, "courses/payment.html", {
        "course": course,
        "payment": payment,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
    })


@login_required
def payment_success_view(request, slug):
    session_id = request.GET.get("session_id")
    course = get_object_or_404(Course, slug=slug, is_published=True)

    if session_id:
        payment = finalize_stripe_payment(session_id)
        if payment:
            messages.success(request, "Payment successful.")
        else:
            messages.warning(request, "Payment not confirmed.")

    return render(request, "courses/payment_success.html", {"course": course})


# ──────────────────────────────────────────────
# Learning View
# ──────────────────────────────────────────────

@login_required
def learn_view(request, slug):
    course = get_object_or_404(Course, slug=slug)
    
    # Security: Check enrollment
    try:
        enrollment = Enrollment.objects.get(
            student=request.user,
            course=course,
            status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED],
        )
    except Enrollment.DoesNotExist:
        messages.error(request, "You must be enrolled to access this course.")
        return redirect("courses:course_detail", slug=slug)

    # Payment Check
    if not course.is_free:
        try:
            if not enrollment.payment.is_completed:
                return redirect("courses:payment", slug=slug)
        except Payment.DoesNotExist:
            return redirect("courses:payment", slug=slug)

    lessons = course.lessons.all().order_by("order")
    
    # Handle specific lesson selection
    lesson_id = request.GET.get("lesson")
    current_lesson = None
    if lesson_id:
        current_lesson = lessons.filter(id=lesson_id).first()
    
    if not current_lesson:
        current_lesson = lessons.first()

    return render(request, "courses/learn.html", {
        "course": course,
        "lessons": lessons,
        "current_lesson": current_lesson,
    })


# ──────────────────────────────────────────────
# Student Dashboard
# ──────────────────────────────────────────────

@login_required
def dashboard_view(request):
    data = get_student_dashboard_data(request.user)
    return render(request, "courses/dashboard.html", data)


# ──────────────────────────────────────────────
# ──────────────────────────────────────────────
# Admin Analytics
# ──────────────────────────────────────────────

@login_required
@admin_required
def admin_analytics_view(request):
    from accounts.models import User

    total_revenue = Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0
    total_users = User.objects.count()
    total_courses = Course.objects.count()
    total_enrollments = Enrollment.objects.count()

    instructors = User.objects.filter(role='instructor').annotate(
        course_count=Count('courses_taught', distinct=True),
        total_students=Count('courses_taught__enrollments', distinct=True),
        revenue_generated=Sum(
            'courses_taught__enrollments__payment__amount',
            filter=Q(courses_taught__enrollments__payment__status='completed')
        )
    )

    return render(request, "admin/analytics_dashboard.html", {
        "total_revenue": total_revenue,
        "total_users": total_users,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "instructors": instructors,
    })


# ──────────────────────────────────────────────
# Static / FAQ Page
# ──────────────────────────────────────────────

def faq_view(request):
    return render(request, "pages/faq.html")

def sitemap_view(request):
    from django.http import HttpResponse
    from django.urls import reverse
    
    courses = Course.objects.filter(is_published=True)
    urls = [
        request.build_absolute_uri(reverse('landing')),
        request.build_absolute_uri(reverse('courses:course_list')),
        request.build_absolute_uri(reverse('courses:faq')),
        request.build_absolute_uri(reverse('courses:contact')),
    ]
    
    for course in courses:
        urls.append(request.build_absolute_uri(reverse('courses:course_detail', kwargs={'slug': course.slug})))
        
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        xml += f'  <url>\n    <loc>{url}</loc>\n    <changefreq>daily</changefreq>\n  </url>\n'
    xml += '</urlset>'
    
    return HttpResponse(xml, content_type="application/xml")

def contact_view(request):
    if request.method == "POST":
        # Process contact form (dummy for now)
        messages.success(request, "Thank you for contacting us! We will get back to you shortly.")
        return redirect("courses:contact")
    return render(request, "pages/contact.html")


# ──────────────────────────────────────────────
# Chatbot API
# ──────────────────────────────────────────────

def chat_api_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    try:
        data = json.loads(request.body)
        query = data.get("message", "").lower().strip()

        if not query:
            return JsonResponse({"response": "It seems you didn't type anything. How can I help?"})

        # ── Greetings ──
        if any(word in query for word in ["hello", "hi", "hey"]):
            return JsonResponse({"response": "Hello! I am your Academic Assistant. I can help you find courses, explain our learning tracks, or assist with your account. How can I help?"})

        # ── Platform Info ──
        if "what is this" in query or "about" in query:
            return JsonResponse({"response": "Academic LMS is a world-class learning platform designed to provide immersive, high-quality education. We offer courses in Programming, Data Science, Arts, and more, taught by industry experts."})

        # ── Enrollment/Pricing ──
        if "cost" in query or "price" in query or "free" in query:
            return JsonResponse({"response": "We offer both Free and Paid courses. You can filter for free courses in our 'Explore' section. Paid courses are priced competitively to ensure quality content."})

        # ── SEO/Visibility ──
        if "sitemap" in query or "indexing" in query:
            return JsonResponse({"response": "Our platform is SEO-optimized with dynamic sitemaps and clean metadata to ensure your profile and courses are discoverable on Google!"})

        # ── Password / reset ──
        if "password" in query or "reset" in query or "forgot" in query:
            return JsonResponse({"response": "No worries! You can reset your password using our secure OTP-based flow. Just go to the Login page and click 'Forgot password?' to get started."})

        # ── Instructor ──
        if "teach" in query or "instructor" in query:
            return JsonResponse({"response": "Join our community of world-class instructors! Click 'Become an Instructor' in the footer to start your journey."})

        # ── Dynamic course search from DB ──
        courses = Course.objects.filter(title__icontains=query, is_published=True)
        if courses.exists():
            course = courses.first()
            if course.is_free:
                return JsonResponse({"response": f"I found a matching course: **'{course.title}'**. Great news, it is completely FREE! Go to 'Available Courses' to enroll."})
            return JsonResponse({"response": f"I found a matching course: **'{course.title}'**. It costs ₹{course.price}. You can find it on the 'Available Courses' page!"})

        # ── Fallback ──
        return JsonResponse({"response": "I am not exactly sure about that, but you can try using our main Search Bar or visiting the FAQ page!"})

    except json.JSONDecodeError:
        return JsonResponse({"response": "I couldn't understand your message. Please try again."}, status=400)
    except Exception as e:
        return JsonResponse({"response": f"I encountered a technical error. Please contact support if this persists."}, status=500)