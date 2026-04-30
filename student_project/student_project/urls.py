from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from courses.views import landing_view

urlpatterns = [
    path("", landing_view, name="landing"),          # Landing page
    path("admin/", admin.site.urls),                 # Admin panel
    path("accounts/", include("accounts.urls")),     # Auth system
    path("accounts/", include("django.contrib.auth.urls")), # Built-in auth (password reset fix)
    path("courses/", include("courses.urls")),       # Course system
    path("instructor/", include("instructor.urls")), # Instructor system
]

# Media files (for development only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)