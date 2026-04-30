from django.urls import path
from courses import views

app_name = "courses"

urlpatterns = [
    path("", views.course_list_view, name="course_list"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("course/<slug:slug>/", views.course_detail_view, name="course_detail"),
    path("course/<slug:slug>/enroll/", views.enroll_view, name="enroll"),
    path("course/<slug:slug>/learn/", views.learn_view, name="learn"),  
    path("course/<slug:slug>/payment/", views.payment_view, name="payment"),
    path("course/<slug:slug>/payment/success/", views.payment_success_view, name="payment_success"),
    
    # Admin & Pages Routes
    path("admin/analytics/", views.admin_analytics_view, name="admin_analytics"),
    path("faq/", views.faq_view, name="faq"),
    path("contact/", views.contact_view, name="contact"),
    path("api/chat/", views.chat_api_view, name="chat_api"),
]