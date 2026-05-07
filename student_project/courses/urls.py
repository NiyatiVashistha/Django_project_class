from django.urls import path
from courses import views

app_name = "courses"

urlpatterns = [
    path("", views.course_list_view, name="course_list"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("course/<slug:slug>/", views.course_detail_view, name="course_detail"),
    path("course/<slug:slug>/enroll/", views.enroll_view, name="enroll"),
    path("course/<slug:slug>/learn/", views.learn_view, name="learn"),
    path("course/<slug:slug>/lesson/<int:lesson_id>/complete/", views.complete_lesson_view, name="complete_lesson"),
    path("course/<slug:slug>/payment/", views.payment_view, name="payment"),
    path("course/<slug:slug>/payment/success/", views.payment_success_view, name="payment_success"),
    path("course/<slug:slug>/review/", views.course_review_view, name="course_review"),
    path("course/<slug:slug>/community/", views.community_chat_view, name="community_chat"),
    
    # Management & Pages Routes
    path("management/analytics/", views.admin_analytics_view, name="admin_analytics"),
    path("management/config/", views.site_config_view, name="site_config"),
    path("management/mail-draft/", views.admin_mail_draft_view, name="admin_mail_draft"),
    path("faq/", views.faq_view, name="faq"),
    path("contact/", views.contact_view, name="contact"),
    path("api/chat/", views.chat_api_view, name="chat_api"),
    
    # Cart URLs
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:course_id>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:course_id>/", views.cart_remove, name="cart_remove"),
    path("cart/checkout/", views.cart_checkout, name="cart_checkout"),

    # Social & Community
    path("instructor/<int:instructor_id>/follow/", views.follow_instructor_view, name="follow_instructor"),
    path("communities/", views.community_list_view, name="community_list"),
    path("communities/create/", views.community_create_view, name="community_create"),
    path("communities/join/<slug:slug>/", views.community_join_view, name="community_join"),
]