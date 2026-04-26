from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache

from .forms import LoginForm, RegisterForm, InstructorSignUpForm


def register_view(request):
    """Register a new student account."""
    if request.user.is_authenticated:
        return redirect("courses:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Auto-login after registration for better UX
            login(request, user)
            messages.success(request, "Account created successfully. Welcome!")
            return redirect("courses:course_list")
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
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome Instructor! You have full access to author courses immediately.")
            return redirect("courses:instructor_dashboard")
    else:
        form = InstructorSignUpForm()

    return render(request, "accounts/instructor_signup.html", {"form": form})


@never_cache
def login_view(request):
    """Login view with secure ?next= redirect handling."""
    # Already logged in — bounce away
    if request.user.is_authenticated:
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
            return redirect(safe_next or "courses:dashboard")
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