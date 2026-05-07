"""
WEB FORMS: THE INPUT GATEKEEPERS
===============================
Forms are the bridge between the User and the Server.
They perform two critical jobs:
1. DATA RENDERING: Generating the HTML (inputs, labels) for the browser.
2. DATA VALIDATION (Sanitization): Ensuring the user didn't type anything 
   dangerous or invalid before it touches our database.
"""

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class RegisterForm(UserCreationForm):
    """
    STUDENT REGISTRATION FORM
    This form creates a new User record. It uses 'UserCreationForm' 
    which automatically handles password hashing (encryption).
    """
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=[(User.Role.STUDENT, 'Student'), (User.Role.INSTRUCTOR, 'Instructor')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial=User.Role.STUDENT,
        help_text="Choose how you want to join our platform."
    )

    class Meta:
        model = User
        fields = ("username", "email", "role")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email.endswith('@gmail.com'):
            raise forms.ValidationError("Registration is restricted to '@gmail.com' addresses.")
        return email


class LoginForm(forms.Form):
    """
    LOGIN FORM: The Authentication Gateway.
    Unlike registration, this doesn't create data; it checks existing data.
    """
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        """
        THE 'CLEAN' METHOD: This is where the magic happens.
        It runs after the fields are checked for basic errors.
        We use it here to verify if the username/password combo is correct.
        """
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        # authenticate() is a built-in Django function that checks the password hash.
        user = authenticate(username=username, password=password)

        if not user:
            raise forms.ValidationError("Invalid credentials")

        cleaned_data["user"] = user
        return cleaned_data


class InstructorSignUpForm(UserCreationForm):
    """
    INSTRUCTOR-SPECIFIC FORM
    We reuse the Registration logic but force the 'Role' to be Instructor.
    """
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control p-2"}),
            "email": forms.EmailInput(attrs={"class": "form-control p-2"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email.endswith('@gmail.com'):
            raise forms.ValidationError("Registration is restricted to '@gmail.com' addresses.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.INSTRUCTOR
        if commit:
            user.save()
        return user


class OTPForm(forms.Form):
    """
    OTP VERIFICATION FORM
    A simple single-field form to capture the 6-digit code.
    """
    otp_code = forms.CharField(max_length=6, widget=forms.TextInput(attrs={"class": "form-control p-2", "placeholder": "Enter 6-digit OTP"}))


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "bio", "profile_pic"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "profile_pic": forms.FileInput(attrs={"class": "form-control"}),
        }
