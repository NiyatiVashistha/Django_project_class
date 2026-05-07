"""
THE CONTROLLER: VIEWS & WORKFLOW
===============================
In Django, 'Views' are the brain of the application. 
They receive the Request (what the user wants) and decide the Response (what the user sees).

THIS FILE HANDLES:
1. USER SESSIONS: Logging in and logging out.
2. AUTHENTICATION FLOW: Verifying who the user is via passwords and OTP.
3. REDIRECT LOGIC: Sending users to the right dashboard after login.
"""

from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail

from accounts.forms import LoginForm, RegisterForm, InstructorSignUpForm, OTPForm, UserProfileForm
import random

User = get_user_model()


@login_required
def profile_edit_view(request):
    """
    Allows users to update their own profile details.
    """
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("courses:dashboard")
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, "accounts/profile_edit.html", {"form": form})


def register_view(request):
    """
    WORKFLOW: STUDENT REGISTRATION
    1. GET: Show the empty registration form.
    2. POST: Receive the typed data.
    3. VALIDATE: Ensure the username isn't taken and email is valid.
    4. SAVE: Create the user in 'Inactive' state (is_active=False).
    5. OTP: Generate a code, save to session, and email it.
    """
    if request.user.is_authenticated:
        return redirect("courses:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False # Security: Don't allow login until OTP is verified.
            user.save()
            
            # Generate a random 6-digit number
            otp_code = str(random.randint(100000, 999999))
            # SESSION: We store the OTP in the server's memory (session) to compare it later.
            request.session['otp_code'] = otp_code
            print(f"\n\n=== STUDENT OTP CODE FOR {user.email}: {otp_code} ===\n\n")
            
            # EMAIL: Sending the code to the user's real inbox (or console in dev).
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
    """Analogous to student registration, but optimized for Instructors."""
    if request.user.is_authenticated:
        return redirect("instructor:dashboard")

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
    """
    WORKFLOW: SECURE LOGIN
    1. VALIDATE: Check credentials via LoginForm.
    2. SESSION START: login(request, user) creates a Session ID.
    3. SECURITY: url_has_allowed_host_and_scheme() prevents 'Open Redirect' attacks.
    """
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
            # SUCCESS: The form verified the password already.
            user = form.cleaned_data["user"]
            login(request, user) # This is where the server 'remembers' the user.
            user.record_login()
            messages.success(request, "Login successful.")

            # ── SECURITY FIX: Validate `next` to prevent Open Redirect attacks ──
            # We ensure the 'next' URL isn't trying to send the user to an evil website.
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
            
            # Default redirects based on Roles
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
    """
    WORKFLOW: OTP VERIFICATION
    1. RETRIEVE: Get the user ID and expected OTP from the Session.
    2. COMPARE: Check if user input matches what the server generated.
    3. ACTIVATE: Set is_active=True so the user can now login.
    """
    user_id = request.session.get('pre_otp_user_id')
    if not user_id:
        return redirect("accounts:login")
        
    user = get_object_or_404(User, id=user_id)
    
    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            otp_input = form.cleaned_data['otp_code']
            session_otp = request.session.get('otp_code')
            
            # The 'Moment of Truth': comparing browser input vs server memory
            if session_otp and session_otp == otp_input:
                user.is_active = True
                user.save()
                
                # Automatically log the user in after successful verification
                login(request, user)
                
                # CLEANUP: Remove temporary data from the session
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


# ──────────────────────────────────────────────
# Forgot Password OTP Flow
# ──────────────────────────────────────────────

def password_reset_request_view(request):
    """
    Step 1 of Password Reset: Find the user and send them an OTP.
    """
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()
        if user:
            otp_code = str(random.randint(100000, 999999))
            request.session['password_reset_otp'] = otp_code
            request.session['password_reset_user_id'] = user.id
            
            print(f"\n\n=== PASSWORD RESET OTP FOR {user.email}: {otp_code} ===\n\n")
            
            send_mail(
                "Password Reset OTP",
                f"Your OTP for password reset is {otp_code}.",
                "noreply@lms.com",
                [user.email],
                fail_silently=False,
            )
            messages.success(request, "OTP sent to your email.")
            return redirect("accounts:password_reset_otp")
        else:
            messages.error(request, "No user found with this email.")
            
    return render(request, "accounts/password_reset_request.html")


def password_reset_otp_verify_view(request):
    """
    Step 2 of Password Reset: Verify the OTP before allowing password change.
    """
    user_id = request.session.get('password_reset_user_id')
    if not user_id:
        return redirect("accounts:password_reset")
        
    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            otp_input = form.cleaned_data['otp_code']
            session_otp = request.session.get('password_reset_otp')
            if session_otp and session_otp == otp_input:
                # Mark as verified in session to 'unlock' the next view
                request.session['password_reset_verified'] = True
                return redirect("accounts:password_reset_change")
            else:
                messages.error(request, "Invalid OTP.")
    else:
        form = OTPForm()
        
    return render(request, "accounts/password_reset_otp.html", {"form": form})


def password_reset_change_view(request):
    """
    Step 3 of Password Reset: Actually update the password in the database.
    """
    # Security: Ensure they actually verified the OTP first
    if not request.session.get('password_reset_verified'):
        return redirect("accounts:password_reset")
        
    user_id = request.session.get('password_reset_user_id')
    user = get_object_or_404(User, id=user_id)
    
    from django.contrib.auth.forms import SetPasswordForm
    
    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save() # This hashes and saves the new password
            # CLEANUP: Important for security
            del request.session['password_reset_user_id']
            del request.session['password_reset_otp']
            del request.session['password_reset_verified']
            
            messages.success(request, "Password reset successful. Please login.")
            return redirect("accounts:login")
    else:
        form = SetPasswordForm(user)
        return render(request, "accounts/password_reset_change.html", {"form": form})
    
    return redirect("accounts:login")


def google_login_view(request):
    """
    MOCK GOOGLE LOGIN
    In a real app, this would use OAuth2 flow. 
    Here, it simulates a successful login for testing.
    """
    # 1. Try to find a 'google_test' user, or create one
    user, created = User.objects.get_or_create(
        username="google_user",
        email="google_user@gmail.com",
        defaults={"is_active": True}
    )
    if created:
        user.set_unusable_password()
        user.save()
    
    # 2. Log them in
    login(request, user)
    messages.success(request, "Logged in with Google (Mock/Test Mode).")
    
    # 3. Redirect to dashboard
    return redirect("courses:dashboard")
