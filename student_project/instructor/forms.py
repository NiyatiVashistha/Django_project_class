from django import forms
from courses.models import Course, Lesson, Category
from django.utils.text import slugify

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'slug', 'description', 'category', 'price', 'difficulty', 'is_published', 'thumbnail']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'content', 'video_url', 'video_file', 'notes_file', 'order', 'duration_minutes', 'is_preview']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 6}),
        }
