from django.urls import path
from . import views

app_name = 'instructor'

urlpatterns = [
    path('dashboard/', views.instructor_dashboard_view, name='dashboard'),
    path('courses/create/', views.course_create_view, name='course_create'),
    path('courses/<slug:slug>/edit/', views.course_edit_view, name='course_edit'),
    path('courses/<slug:slug>/delete/', views.course_delete_view, name='course_delete'),
    path('courses/<slug:slug>/publish/', views.course_toggle_publish_view, name='course_toggle_publish'),
    path('courses/<slug:slug>/lessons/create/', views.lesson_create_view, name='lesson_create'),
]
