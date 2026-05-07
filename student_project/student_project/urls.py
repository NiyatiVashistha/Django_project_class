from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.shortcuts import redirect
from django.views.generic import TemplateView
from courses.views import landing_view, sitemap_view

urlpatterns = [
    path("", landing_view, name="landing"),
    # SECURE CONSOLE: Renamed from 'admin/' to hide the entry point from bots and attackers.
    path("lms-secure-console/", admin.site.urls),
    # DECOY: Redirects standard admin attempts to the landing page to smartly handle intruders.
    path("admin/", lambda r: redirect('landing', permanent=False)),
    
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("courses/", include("courses.urls")),
    path("instructor/", include("instructor.urls")),
    
    # SEO
    path("sitemap.xml", sitemap_view, name="sitemap"),
    path("robots.txt", TemplateView.as_view(template_name="seo/robots.txt", content_type="text/plain")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)