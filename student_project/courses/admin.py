from django.contrib import admin

from courses.models import Category, Course, Lesson, Enrollment, Payment, CategoryRequest, Review, Community, CommunityMessage


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug")
    list_filter = ("parent",)
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


@admin.register(CategoryRequest)
class CategoryRequestAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "instructor", "is_approved", "created_at")
    list_filter = ("is_approved",)
    actions = ['approve_requests']

    def approve_requests(self, request, queryset):
        from django.utils.text import slugify
        count = 0
        for req in queryset.filter(is_approved=False):
            Category.objects.get_or_create(
                name=req.name,
                defaults={
                    'slug': slugify(req.name),
                    'parent': req.parent
                }
            )
            req.is_approved = True
            req.save()
            count += 1
        self.message_user(request, f"{count} category requests approved.")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "rating", "created_at")
    list_filter = ("rating", "course")


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "creator")


@admin.register(CommunityMessage)
class CommunityMessageAdmin(admin.ModelAdmin):
    list_display = ("user", "community", "timestamp")
    list_filter = ("community", "timestamp")