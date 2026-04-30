from django import forms
from courses.models import Course, Lesson, Category
from django.utils.text import slugify

class CourseForm(forms.ModelForm):
    new_category = forms.CharField(
        required=False, 
        label="Create New Category",
        help_text="If your category is not in the list, type it here to create it.",
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Advanced Calculus'})
    )

    class Meta:
        model = Course
        fields = ['title', 'slug', 'description', 'category', 'new_category', 'price', 'difficulty', 'is_published', 'thumbnail']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def save(self, commit=True):
        course = super().save(commit=False)
        new_cat_name = self.cleaned_data.get('new_category')
        if new_cat_name:
            category, created = Category.objects.get_or_create(
                name=new_cat_name,
                defaults={'slug': slugify(new_cat_name)}
            )
            course.category = category
        if commit:
            course.save()
        return course

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'content', 'video_url', 'video_file', 'notes_file', 'order', 'duration_minutes', 'is_preview']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 6}),
        }
