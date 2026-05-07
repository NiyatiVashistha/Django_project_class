from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from accounts import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("instructor/signup/", views.instructor_signup_view, name="instructor_signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("otp-verify/", views.otp_verify_view, name="otp_verify"),
    path("profile/edit/", views.profile_edit_view, name="profile_edit"),
    path("google-login/", views.google_login_view, name="google_login"),
    
    # Password Reset Features (OTP-based)
    path("password-reset/", views.password_reset_request_view, name="password_reset"),
    path("password-reset/otp/", views.password_reset_otp_verify_view, name="password_reset_otp"),
    path("password-reset/change/", views.password_reset_change_view, name="password_reset_change"),
]