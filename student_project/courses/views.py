"""
THE APPLICATION ENGINE: VIEWS & APIS
====================================
This file controls the heart of the Learning Management System.
It handles everything from displaying course lists to processing AJAX chat requests.

KEY CONCEPTS:
1. AJAX (Asynchronous JavaScript and XML): Communicating with the server without 
   refreshing the page (used in the Chatbot).
2. JSON (JavaScript Object Notation): The data format used for AJAX communication.
3. DECORATORS: Like @login_required, which check permissions before running a function.
4. SERVER-SIDE RENDERING: Using Python to create the HTML pages the user sees.
"""

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
from django.utils import timezone

from courses.models import Course, Enrollment, Lesson, Payment, Review, Community, CommunityMessage, Category, LessonProgress
from courses.services import (
    search_courses,
    enroll_student,
    is_enrolled,
    create_stripe_checkout_session,
    finalize_stripe_payment,
    get_student_dashboard_data,
    log_course_activity,
    get_admin_analytics_data,
)


# ──────────────────────────────────────────────
# Decorators
# ──────────────────────────────────────────────

def instructor_required(view_func):
    """Allow only users whose role is 'instructor' or 'admin'."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.is_instructor or request.user.role == 'admin'):
            raise PermissionDenied("Only instructors and administrators can access this area.")
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
    reviews = course.reviews.all().order_by("-created_at")

    return render(request, "courses/course_detail.html", {
        "course": course,
        "lessons": lessons,
        "enrolled": enrolled,
        "reviews": reviews,
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

    # Calculate Progress
    total_lessons = lessons.count()
    completed_lessons = LessonProgress.objects.filter(
        user=request.user,
        lesson__course=course,
        is_completed=True
    )
    completed_lessons_count = completed_lessons.count()
    completed_lesson_ids = list(completed_lessons.values_list("lesson_id", flat=True))
    progress_percent = int((completed_lessons_count / total_lessons) * 100) if total_lessons > 0 else 0

    return render(request, "courses/learn.html", {
        "course": course,
        "lessons": lessons,
        "current_lesson": current_lesson,
        "progress_percent": progress_percent,
        "completed_lesson_ids": completed_lesson_ids,
    })


@login_required
@require_http_methods(["POST"])
def complete_lesson_view(request, slug, lesson_id):
    course = get_object_or_404(Course, slug=slug)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    
    # Mark as completed
    progress, created = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
        defaults={'is_completed': True}
    )
    if not created:
        progress.is_completed = True
        progress.save()
    
    # Find next lesson
    next_lesson = course.lessons.filter(order__gt=lesson.order).order_by('order').first()
    
    if next_lesson:
        redirect_url = reverse('courses:learn', kwargs={'slug': slug})
        return redirect(f"{redirect_url}?lesson={next_lesson.id}")
    else:
        # Course completed!
        messages.success(request, f"Congratulations! You've completed {course.title}.")
        return redirect("courses:dashboard")


# ──────────────────────────────────────────────
# Student Dashboard
# ──────────────────────────────────────────────

@login_required
def dashboard_view(request):
    data = get_student_dashboard_data(request.user)
    return render(request, "courses/dashboard.html", data)


# ──────────────────────────────────────────────
# Static / FAQ Page
# ──────────────────────────────────────────────

def faq_view(request):
    """A simple view to render the FAQ page."""
    return render(request, "pages/faq.html")

def sitemap_view(request):
    """
    SEO FEATURE: Dynamic Sitemap
    This view generates an XML file that tells Google about all the pages 
    on our site, helping us rank higher in search results.
    """
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
    """Handles the contact form submission."""
    if request.method == "POST":
        from courses.models import ContactMessage
        name = request.POST.get("name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")
        
        if name and email and message:
            ContactMessage.objects.create(
                name=name,
                email=email,
                subject=subject or "General Inquiry",
                message=message
            )
            messages.success(request, "Thank you for contacting us! We have received your message.")
        else:
            messages.error(request, "Please fill in all required fields.")
            
        return redirect("courses:contact")
    return render(request, "pages/contact.html")


# ──────────────────────────────────────────────
# Chatbot API (The AJAX/JSON Hub)
# ──────────────────────────────────────────────

def chat_api_view(request):
    """
    HOW AJAX WORKS HERE:
    1. The Browser (Client) sends a background request using JavaScript's fetch().
    2. The request contains a 'JSON' string in the body.
    3. The Server (this Python code) reads the JSON, processes it, and sends back
       a 'JsonResponse' (more JSON).
    4. The Browser receives the response and updates the chat window without 
       reloading the whole page.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    try:
        # JSON DECODING: Turning the raw string from the browser back into a Python dictionary.
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
        # IMPROVEMENT: Instead of searching the whole query string, we extract keywords if needed
        # or search if the query itself is short and likely a course name.
        search_query = query
        if len(query.split()) > 4:
            # If query is long, it's likely a sentence like "I want to learn python"
            # We try to extract common course keywords.
            keywords = ["python", "java", "web", "design", "business", "data", "marketing"]
            found_keywords = [w for w in keywords if w in query]
            if found_keywords:
                search_query = found_keywords[0]

        from django.db.models import Q
        courses = Course.objects.filter(
            Q(title__icontains=search_query) | Q(category__name__icontains=search_query), 
            is_published=True
        )
        
        bot_response = ""
        if courses.exists():
            course = courses.first()
            if course.is_free:
                bot_response = f"I found a matching course: **'{course.title}'**. Great news, it is completely FREE! Go to 'Available Courses' to enroll."
            else:
                bot_response = f"I found a matching course: **'{course.title}'**. It costs ₹{course.price}. You can find it on the 'Available Courses' page!"
        elif "course" in query or "learn" in query:
             bot_response = "We have many courses! You can check our 'Explore Courses' page to see everything we offer in Programming, Business, and more."
        else:
            bot_response = "I am not exactly sure about that, but you can try using our main Search Bar or visiting the FAQ page!"

        # ── LOGGING: Save the chat for staff analysis ──
        try:
            from courses.models import ChatLog
            ChatLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                message=query,
                response=bot_response
            )
        except:
            # If logging fails (e.g. table not created), we don't want to crash the whole chat.
            pass

        return JsonResponse({"response": bot_response})

    except json.JSONDecodeError:
        return JsonResponse({"response": "I couldn't understand your message. Please try again."}, status=400)
    except Exception as e:
        # CATCH-ALL ERROR HANDLING: Ensures the server doesn't crash if something goes wrong.
        return JsonResponse({"response": f"I encountered a technical error. Please contact support if this persists."}, status=500)


@admin_required
def admin_analytics_view(request):
    """
    ADMIN VIEW: Displays the platform analytics dashboard.
    """
    data = get_admin_analytics_data()
    return render(request, "courses/admin_analytics.html", data)


@admin_required
def site_config_view(request):
    """
    ADMIN VIEW: Allows dynamic layout and branding changes.
    """
    from courses.models import SiteConfiguration
    from courses.forms import SiteConfigurationForm
    from django.db import OperationalError, ProgrammingError

    try:
        config = SiteConfiguration.objects.first()
    except (OperationalError, ProgrammingError):
        config = None
    if request.method == "POST":
        form = SiteConfigurationForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Site configuration updated successfully!")
            return redirect("courses:admin_analytics")
    else:
        form = SiteConfigurationForm(instance=config)
    
    return render(request, "courses/site_config.html", {"form": form})


# ──────────────────────────────────────────────
# Cart Management (Session-based for Guests & Users)
# ──────────────────────────────────────────────

def cart_view(request):
    """Displays the current items in the user's cart."""
    cart = request.session.get('cart', {})
    course_ids = cart.keys()
    courses = Course.objects.filter(id__in=course_ids)
    
    total_price = sum(course.price for course in courses)
    
    return render(request, "courses/cart.html", {
        "courses": courses,
        "total_price": total_price
    })


def cart_add(request, course_id):
    """Adds a course to the session-based cart."""
    course = get_object_or_404(Course, id=course_id, is_published=True)
    cart = request.session.get('cart', {})
    
    # Check if already enrolled (if logged in)
    if request.user.is_authenticated:
        if Enrollment.objects.filter(student=request.user, course=course).exists():
            messages.info(request, f"You are already enrolled in '{course.title}'.")
            return redirect("courses:course_detail", slug=course.slug)

    # Use course_id as string key for JSON session compatibility
    course_id_str = str(course_id)
    if course_id_str not in cart:
        cart[course_id_str] = 1 # We only need 1 of each course
        request.session['cart'] = cart
        messages.success(request, f"'{course.title}' added to your cart!")
    else:
        messages.info(request, f"'{course.title}' is already in your cart.")
        
    return redirect("courses:cart")


@login_required
@require_http_methods(["POST"])
def cart_checkout(request):
    """Enrolls the user in all courses in the cart and processes payment requirements."""
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect("courses:course_list")
        
    course_ids = cart.keys()
    courses = Course.objects.filter(id__in=course_ids)
    
    any_paid = False
    first_paid_slug = None
    
    for course in courses:
        enrollment, created = enroll_student(request.user, course)
        if not course.is_free and not any_paid:
            # Check if already paid
            if not Payment.objects.filter(enrollment=enrollment, status=Payment.Status.COMPLETED).exists():
                any_paid = True
                first_paid_slug = course.slug
            
    # Clear cart after processing
    request.session['cart'] = {}
    
    if any_paid:
        messages.success(request, "Enrollment initiated. Please complete payment for the course.")
        return redirect("courses:payment", slug=first_paid_slug)
    
    messages.success(request, "Successfully enrolled in all courses from your cart!")
    return redirect("courses:dashboard")


def cart_remove(request, course_id):
    """Removes a course from the session-based cart."""
    cart = request.session.get('cart', {})
    course_id_str = str(course_id)
    
    if course_id_str in cart:
        del cart[course_id_str]
        request.session['cart'] = cart
        messages.success(request, "Course removed from cart.")
        
    return redirect("courses:cart")


@login_required
def follow_instructor_view(request, instructor_id):
    """Allows a student to follow or unfollow an instructor."""
    from accounts.models import User, Follow
    instructor = get_object_or_404(User, id=instructor_id, role=User.Role.INSTRUCTOR)
    
    if instructor == request.user:
        messages.error(request, "You cannot follow yourself.")
        return redirect("courses:course_list")

    follow, created = Follow.objects.get_or_create(student=request.user, instructor=instructor)
    
    if not created:
        follow.delete()
        messages.success(request, f"You have unfollowed {instructor.username}.")
    else:
        messages.success(request, f"You are now following {instructor.username}!")
        
    return redirect(request.META.get('HTTP_REFERER', 'courses:course_list'))


def community_list_view(request):
    """Displays all available communities."""
    from courses.models import Community
    communities = Community.objects.all()
    return render(request, "courses/community_list.html", {"communities": communities})


@login_required
def community_join_view(request, slug):
    """Allows a user to join or leave a community."""
    from courses.models import Community
    community = get_object_or_404(Community, slug=slug)
    
    if request.user in community.members.all():
        community.members.remove(request.user)
        messages.success(request, f"You have left the {community.name} community.")
    else:
        community.members.add(request.user)
        messages.success(request, f"Welcome to the {community.name} community!")
        
    return redirect("courses:community_list")


@admin_required
def admin_mail_draft_view(request):
    """Allows admins to draft emails and 'send' them (logically)."""
    from courses.models import MailDraft
    from accounts.models import User
    
    if request.method == "POST":
        subject = request.POST.get("subject")
        body = request.POST.get("body")
        recipient_type = request.POST.get("recipient_type")
        
        draft = MailDraft.objects.create(
            subject=subject,
            body=body,
            recipient_type=recipient_type,
            sent_at=timezone.now() # Simulate sending immediately
        )
        
        # Logically 'sending' (in a real app, use send_mail() here)
        messages.success(request, f"Email '{subject}' sent to {recipient_type} recipients!")
        return redirect("courses:admin_analytics")
        
    return render(request, "courses/admin_mail_draft.html")


@login_required
def community_create_view(request):
    """Allows instructors and admins to create a new community."""
    from accounts.models import User
    if request.user.role not in [User.Role.INSTRUCTOR, User.Role.ADMIN]:
        messages.error(request, "Only instructors or admins can create communities.")
        return redirect("courses:community_list")
        
    from courses.forms import CommunityForm
    from courses.models import Community
    if request.method == "POST":
        form = CommunityForm(request.POST, request.FILES)
        if form.is_valid():
            community = form.save(commit=False)
            community.creator = request.user
            community.save()
            community.members.add(request.user)
            messages.success(request, f"Community '{community.name}' created successfully!")
            return redirect("courses:community_list")
    else:
        form = CommunityForm()
    
    return render(request, "courses/community_form.html", {"form": form})


@login_required
def course_review_view(request, slug):
    from courses.forms import ReviewForm
    from accounts.models import User
    
    course = get_object_or_404(Course, slug=slug)
    
    # Only students who are enrolled can leave reviews
    if request.user.role != User.Role.STUDENT:
        messages.error(request, "Only students can leave reviews.")
        return redirect("courses:course_detail", slug=slug)
        
    if not is_enrolled(request.user, course):
        messages.error(request, "You must be enrolled to leave a review.")
        return redirect("courses:course_detail", slug=slug)
    
    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            Review.objects.update_or_create(
                course=course, student=request.user,
                defaults={'rating': form.cleaned_data['rating'], 'comment': form.cleaned_data['comment']}
            )
            messages.success(request, "Thank you for your feedback!")
            return redirect("courses:course_detail", slug=slug)
    else:
        existing_review = Review.objects.filter(course=course, student=request.user).first()
        form = ReviewForm(instance=existing_review)
    
    return render(request, "courses/review_form.html", {"course": course, "form": form})


@login_required
def community_chat_view(request, slug):
    course = get_object_or_404(Course, slug=slug)
    is_authorized = (
        is_enrolled(request.user, course) or 
        course.instructor == request.user or 
        request.user.role == 'admin'
    )
    
    if not is_authorized:
        messages.error(request, "Access restricted to course participants.")
        return redirect("courses:course_detail", slug=slug)
    
    community = getattr(course, 'community', None)
    if not community:
        community = Community.objects.create(
            name=f"{course.title} Community",
            course=course,
            creator=course.instructor or request.user,
            description=f"Official community for students of {course.title}"
        )
    
    if request.method == "POST":
        content = request.POST.get("content")
        if content:
            CommunityMessage.objects.create(community=community, user=request.user, content=content)
            return redirect("courses:community_chat", slug=slug)

    messages_list = community.messages.all().order_by("-timestamp")[:100]
    return render(request, "courses/community_chat.html", {
        "course": course,
        "community": community,
        "messages_list": reversed(messages_list)
    })