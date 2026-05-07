from django.contrib import admin
from accounts.models import User, Student, Instructor

# MASTER USER LIST
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email")
    readonly_fields = ("last_login_time", "date_joined")

# DEDICATED STUDENT LIST
@admin.register(Student)
class StudentAdmin(UserAdmin):
    """Admin view for Students only."""
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=User.Role.STUDENT)

# DEDICATED INSTRUCTOR LIST
@admin.register(Instructor)
class InstructorAdmin(UserAdmin):
    """Admin view for Instructors only."""
    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=User.Role.INSTRUCTOR)
