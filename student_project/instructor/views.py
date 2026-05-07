from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q

from courses.models import Course, Lesson, Payment, CategoryRequest, Category
from instructor.forms import CourseForm, LessonForm
from courses.views import instructor_required

@login_required
@instructor_required
def instructor_dashboard_view(request):
    courses = Course.objects.filter(instructor=request.user).annotate(
        enrollment_count=Count('enrollments', distinct=True),
        total_revenue=Sum(
            'enrollments__payment__amount',
            filter=Q(enrollments__payment__status=Payment.Status.COMPLETED)
        )
    )
    
    # Aggregate stats for the header
    total_revenue = courses.aggregate(total=Sum('total_revenue'))['total'] or 0
    total_students_count = courses.aggregate(total=Sum('enrollment_count'))['total'] or 0
    
    return render(request, "instructor/instructor_dashboard.html", {
        "courses": courses,
        "total_revenue": total_revenue,
        "total_students_count": total_students_count
    })


@login_required
@instructor_required
def course_create_view(request):
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            course.save()
            messages.success(request, "Course successfully created!")
            return redirect("instructor:dashboard")
    else:
        form = CourseForm()
    return render(request, "instructor/course_form.html", {"form": form})


@login_required
@instructor_required
def lesson_create_view(request, slug):
    course = get_object_or_404(Course, slug=slug, instructor=request.user)

    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            if Lesson.objects.filter(course=course, order=lesson.order).exists():
                messages.error(request, f"Chapter {lesson.order} already exists for this course!")
            else:
                lesson.save()
                messages.success(request, "Chapter successfully added to course!")
                return redirect("instructor:dashboard")
    else:
        next_order = course.lessons.count() + 1
        form = LessonForm(initial={"order": next_order})

    return render(request, "instructor/lesson_form.html", {"form": form, "course": course})


@login_required
@instructor_required
def course_edit_view(request, slug):
    course = get_object_or_404(Course, slug=slug, instructor=request.user)
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course updated successfully!")
            return redirect("instructor:dashboard")
    else:
        form = CourseForm(instance=course)
    return render(request, "instructor/course_form.html", {"form": form, "course": course, "is_edit": True})


@login_required
@instructor_required
@require_http_methods(["POST"])
def course_delete_view(request, slug):
    course = get_object_or_404(Course, slug=slug, instructor=request.user)
    course.delete()
    messages.success(request, "Course deleted successfully.")
    return redirect("instructor:dashboard")


@login_required
@instructor_required
@require_http_methods(["POST"])
def course_toggle_publish_view(request, slug):
    course = get_object_or_404(Course, slug=slug, instructor=request.user)
    course.is_published = not course.is_published
    course.save()
    status = "published" if course.is_published else "hidden"
    messages.success(request, f"Course successfully {status}!")
    return redirect("instructor:dashboard")


@login_required
@instructor_required
def lesson_edit_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, course__instructor=request.user)
    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, "Chapter updated successfully!")
            return redirect("instructor:dashboard")
    else:
        form = LessonForm(instance=lesson)
    return render(request, "instructor/lesson_form.html", {"form": form, "course": lesson.course, "is_edit": True})


@login_required
@instructor_required
@require_http_methods(["POST"])
def lesson_delete_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, course__instructor=request.user)
    lesson.delete()
    messages.success(request, "Chapter deleted successfully.")
    return redirect("instructor:dashboard")


@login_required
@instructor_required
def category_request_view(request):
    from courses.forms import CategoryRequestForm
    if request.method == "POST":
        form = CategoryRequestForm(request.POST)
        if form.is_valid():
            cat_request = form.save(commit=False)
            cat_request.instructor = request.user
            cat_request.save()
            messages.success(request, "Category request submitted! Admin will review it.")
            return redirect("instructor:dashboard")
    else:
        form = CategoryRequestForm()
    
    requests = CategoryRequest.objects.filter(instructor=request.user).order_by('-created_at')
    return render(request, "instructor/category_request.html", {"form": form, "requests": requests})
