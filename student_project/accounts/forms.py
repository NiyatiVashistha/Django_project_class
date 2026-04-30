from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class RegisterForm(UserCreationForm):
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


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        user = authenticate(username=username, password=password)

        if not user:
            raise forms.ValidationError("Invalid credentials")

        cleaned_data["user"] = user
        return cleaned_data


class InstructorSignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control p-2"}),
            "email": forms.EmailInput(attrs={"class": "form-control p-2"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.INSTRUCTOR
        if commit:
            user.save()
        return user


class OTPForm(forms.Form):
    otp_code = forms.CharField(max_length=6, widget=forms.TextInput(attrs={"class": "form-control p-2", "placeholder": "Enter 6-digit OTP"}))