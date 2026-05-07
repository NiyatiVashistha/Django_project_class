from django import forms


class SearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "What do you want to learn?",
        }),
    )
    category = forms.ModelChoiceField(
        queryset=None, # Will set in __init__
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    sort = forms.ChoiceField(
        choices=[
            ("", "Sort By"),
            ("newest", "Newest"),
            ("popular", "Most Popular"),
            ("price_low", "Price: Low to High"),
            ("price_high", "Price: High to Low"),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from courses.models import Category
        self.fields['category'].queryset = Category.objects.all()


class PaymentForm(forms.Form):
    cardholder_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-input"}),
    )

    def clean_cardholder_name(self):
        value = self.cleaned_data["cardholder_name"].strip()
        if not value:
            raise forms.ValidationError("Cardholder name is required.")
        return value


class SiteConfigurationForm(forms.ModelForm):
    class Meta:
        from courses.models import SiteConfiguration
        model = SiteConfiguration
        fields = [
            'site_name', 'site_logo', 'primary_color', 'secondary_color',
            'hero_title', 'hero_subtitle', 'layout_type',
            'announcement_text', 'show_announcement',
            'offer_text', 'offer_link', 'show_offer',
            'facebook_url', 'twitter_url', 'linkedin_url', 'instagram_url',
            'contact_email', 'contact_phone', 'office_address'
        ]
        widgets = {
            'site_name': forms.TextInput(attrs={'class': 'form-control'}),
            'primary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'hero_title': forms.TextInput(attrs={'class': 'form-control'}),
            'hero_subtitle': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'layout_type': forms.Select(attrs={'class': 'form-select'}),
            'announcement_text': forms.TextInput(attrs={'class': 'form-control'}),
            'show_announcement': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'offer_text': forms.TextInput(attrs={'class': 'form-control'}),
            'offer_link': forms.TextInput(attrs={'class': 'form-control'}),
            'show_offer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        from courses.models import Review
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, f"{i} Stars") for i in range(5, 0, -1)], attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Share your experience...'}),
        }


class CategoryRequestForm(forms.ModelForm):
    class Meta:
        from courses.models import CategoryRequest
        model = CategoryRequest
        fields = ['name', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Data Science'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from courses.models import Category
        self.fields['parent'].queryset = Category.objects.filter(parent__isnull=True)
        self.fields['parent'].empty_label = "New Root Category"


class CommunityForm(forms.ModelForm):
    class Meta:
        from courses.models import Community
        model = Community
        fields = ['name', 'description', 'thumbnail']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }