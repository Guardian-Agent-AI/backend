from django import forms
from django.contrib.auth.models import User
from .models import ContactMessage


class RegistrationForm(forms.Form):
    """Account creation form with phone number."""
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'First name',
    }))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Last name',
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'you@example.com',
    }))
    phone_number = forms.CharField(max_length=17, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': '+1234567890',
    }))
    password = forms.CharField(min_length=8, widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Min. 8 characters',
    }))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Repeat password',
    }))
    children_count = forms.IntegerField(min_value=1, max_value=10, initial=1, widget=forms.NumberInput(attrs={
        'class': 'form-control', 'min': 1, 'max': 10,
    }))

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password_confirm'):
            self.add_error('password_confirm', 'Passwords do not match.')
        return cleaned


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'you@example.com',
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Password',
    }))


class AccountSettingsForm(forms.Form):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control',
    }))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control',
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
    }))
    phone_number = forms.CharField(max_length=17, widget=forms.TextInput(attrs={
        'class': 'form-control',
    }))
    children_count = forms.IntegerField(min_value=1, max_value=10, widget=forms.NumberInput(attrs={
        'class': 'form-control', 'min': 1, 'max': 10,
    }))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user

    def clean_email(self):
        email = self.cleaned_data['email']
        qs = User.objects.filter(email=email)
        if self._user:
            qs = qs.exclude(pk=self._user.pk)
        if qs.exists():
            raise forms.ValidationError('This email is already in use.')
        return email


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
    }))
    new_password = forms.CharField(min_length=8, widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Min. 8 characters',
    }))
    new_password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
    }))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('new_password_confirm'):
            self.add_error('new_password_confirm', 'Passwords do not match.')
        return cleaned


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'you@example.com',
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'How can we help?',
            }),
        }
