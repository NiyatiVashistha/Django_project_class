from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail

from .forms import LoginForm, RegisterForm, InstructorSignUpForm, OTPForm
import random

User = get_user_model()


def register_view(request):
    """Register a new student account."""
    if request.user.is_authenticated:
        return redirect("courses:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            
            otp_code = str(random.randint(100000, 999999))
            request.session['otp_code'] = otp_code
            print(f"\n\n=== STUDENT OTP CODE FOR {user.email}: {otp_code} ===\n\n")
            
            send_mail(
                "Your LMS OTP Verification Code",
                f"Your OTP code is {otp_code}. It is valid for 10 minutes.",
                "noreply@lms.com",
                [user.email],
                fail_silently=False,
            )
            
            request.session['pre_otp_user_id'] = user.id
            messages.success(request, "Account created! Please check your email for the OTP.")
            return redirect("accounts:otp_verify")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def instructor_signup_view(request):
    """Register a new instructor account."""
    if request.user.is_authenticated:
        return redirect("courses:instructor_dashboard")

    if request.method == "POST":
        form = InstructorSignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            
            otp_code = str(random.randint(100000, 999999))
            request.session['otp_code'] = otp_code
            print(f"\n\n=== INSTRUCTOR OTP CODE FOR {user.email}: {otp_code} ===\n\n")
            
            send_mail(
                "Your LMS Instructor OTP Verification",
                f"Your OTP code is {otp_code}. It is valid for 10 minutes.",
                "noreply@lms.com",
                [user.email],
                fail_silently=False,
            )
            
            request.session['pre_otp_user_id'] = user.id
            messages.success(request, "Instructor account created! Please check your email for the OTP.")
            return redirect("accounts:otp_verify")
    else:
        form = InstructorSignUpForm()

    return render(request, "accounts/instructor_signup.html", {"form": form})


@never_cache
def login_view(request):
    """Login view with secure ?next= redirect handling."""
    # Already logged in — bounce away
    if request.user.is_authenticated:
        if request.user.role == 'admin':
            return redirect("courses:admin_analytics")
        elif request.user.is_instructor:
            return redirect("instructor:dashboard")
        return redirect("courses:dashboard")

    # Capture the ?next= redirect destination (set automatically by @login_required)
    next_url = request.POST.get("next") or request.GET.get("next") or ""

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)
            user.record_login()
            messages.success(request, "Login successful.")

            # ── SECURITY FIX: Validate `next` to prevent Open Redirect attacks ──
            # url_has_allowed_host_and_scheme() rejects any URL pointing to a
            # different host (e.g. https://evil.com) or using a dangerous scheme.
            safe_next = (
                next_url
                if next_url and url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                )
                else None
            )
            if safe_next:
                return redirect(safe_next)
            
            if user.role == 'admin':
                return redirect("courses:admin_analytics")
            elif user.is_instructor:
                return redirect("instructor:dashboard")
            return redirect("courses:dashboard")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form, "next": next_url})


def logout_view(request):
    """Logout — only accepts POST to prevent CSRF-based forced logouts."""
    if request.method == "POST":
        logout(request)
        messages.info(request, "Logged out successfully.")
        return redirect("courses:course_list")

    return render(request, "accounts/logout_confirm.html")


def otp_verify_view(request):
    user_id = request.session.get('pre_otp_user_id')
    if not user_id:
        return redirect("accounts:login")
        
    user = get_object_or_404(User, id=user_id)
    
    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            otp_input = form.cleaned_data['otp_code']
            session_otp = request.session.get('otp_code')
            if session_otp and session_otp == otp_input:
                user.is_active = True
                user.save()
                
                login(request, user)
                del request.session['pre_otp_user_id']
                if 'otp_code' in request.session:
                    del request.session['otp_code']
                
                messages.success(request, "OTP Verified successfully. Welcome!")
                if user.is_instructor:
                    return redirect("instructor:dashboard")
                return redirect("courses:dashboard")
            else:
                messages.error(request, "Invalid or expired OTP.")
    else:
        form = OTPForm()
        
    return render(request, "accounts/otp_verify.html", {"form": form})