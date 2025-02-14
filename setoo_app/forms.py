# setoo_app/forms.py
from django import forms

class APIKeyForm(forms.Form):
    api_key = forms.CharField(
        label='API Key',  # Set a more descriptive label
        max_length=255,
        widget=forms.PasswordInput( # Mask the input
            attrs={'class': 'form-control', 'placeholder': 'Enter your API key'} # Add attributes for styling
        ),
        required=True, # Make the field required
        help_text="Please enter your API key." # Add help text
    )

    def clean_api_key(self):  # Optional: Add custom validation
        api_key = self.cleaned_data['api_key']
        # Add your custom validation logic here if needed.
        # For example, you could check if the API key meets certain criteria.
        # if not meets criteria:
        #    raise forms.ValidationError("Invalid API key format.")
        return api_key