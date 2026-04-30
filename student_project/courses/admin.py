from django.contrib import admin

from courses.models import Category, Course, Lesson, Enrollment, Payment


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "difficulty", "is_published", "instructor", "category")
    list_filter = ("is_published", "difficulty", "category")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order", "is_preview")
    list_filter = ("is_preview", "course")
    search_fields = ("title", "content")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "status", "enrolled_at")
    list_filter = ("status", "course")
    search_fields = ("student__username", "course__title")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "amount", "status", "paid_at", "gateway")
    list_filter = ("status", "gateway")
    search_fields = ("enrollment__student__username", "enrollment__course__title")