from django.contrib import admin
from courses.models import Category, Course, Lesson, Enrollment, Payment

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    # prepopulated_fields dynamically generates the slug in the UI as you type the name!
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "instructor", "price", "difficulty", "is_published")
    list_filter = ("is_published", "difficulty", "category")
    search_fields = ("title", "description", "instructor__username")
    prepopulated_fields = {"slug": ("title",)}
    
    # EDUCATIONAL COMMENT: 
    # Use raw_id_fields for ForeignKeys that might have thousands of records (like User).
    # It replaces a massive dropdown with a simple ID lookup magnifying glass.
    raw_id_fields = ("instructor",)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("course", "order", "title", "duration_minutes", "is_preview")
    list_filter = ("course", "is_preview")
    search_fields = ("title", "course__title")

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "status", "enrolled_at")
    list_filter = ("status", "enrolled_at")
    raw_id_fields = ("student", "course")

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "amount", "status", "gateway", "paid_at")
    list_filter = ("status", "gateway")
    readonly_fields = ("paid_at", "created_at", "gateway_order_id", "gateway_payment_id", "gateway_signature")
