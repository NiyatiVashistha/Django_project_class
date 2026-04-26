from django import forms

from courses.models import Course, Category, Lesson

class SearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(attrs={
            "class": "form-control p-2",
            "placeholder": "Search courses...", 
        }),
    )
    sort = forms.ChoiceField(
        required=False,
        label="",
        choices=[
            ("", "Sort By"),
            ("newest", "Newest"),
            ("created_at", "Oldest"),
            ("popular", "Most Popular"),
            ("free", "Free"),
        ],
        widget=forms.Select(attrs={"class": "form-select p-2"}),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        label="",
        widget=forms.Select(attrs={"class": "form-select p-2"})
    )


class PaymentForm(forms.Form):
    cardholder_name = forms.CharField(
        max_length=100, widget=forms.TextInput(attrs={"class": "form-input"}),
    )

    def clean_cardholder_name(self):
        value = self.cleaned_data["cardholder_name"].strip() 
        if not value:
            raise forms.ValidationError("Cardholder name is required.") 
        return value

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "description", "category", "price", "difficulty", "is_published", "thumbnail"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control p-2"}),
            "description": forms.Textarea(attrs={"class": "form-control p-2", "rows": 4}),
            "category": forms.Select(attrs={"class": "form-select p-2"}),
            "price": forms.NumberInput(attrs={"class": "form-control p-2", "step": "0.01"}),
            "difficulty": forms.Select(attrs={"class": "form-select p-2"}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input mt-2", "style":"transform: scale(1.5)", "role": "switch"}),
            "thumbnail": forms.FileInput(attrs={"class": "form-control p-2"}),
        }

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["title", "content", "order", "duration_minutes"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control p-2"}),
            "content": forms.Textarea(attrs={"class": "form-control p-2", "rows": 8}),
            "order": forms.NumberInput(attrs={"class": "form-control p-2", "min": "1"}),
            "duration_minutes": forms.NumberInput(attrs={"class": "form-control p-2", "min": "1"}),
        }