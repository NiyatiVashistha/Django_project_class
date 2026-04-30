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