from django import forms


class SearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={
            "class": "search-input",
            "placeholder": "Search courses...",
        }),
    )


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