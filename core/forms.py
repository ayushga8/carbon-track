"""Forms for the core application."""

from django import forms


class ContactForm(forms.Form):
    """Contact form with accessible widgets and validation."""

    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your full name',
            'aria-label': 'Your full name',
            'autocomplete': 'name',
        }),
        error_messages={
            'required': 'Please enter your name.',
            'max_length': 'Name cannot exceed 100 characters.',
        },
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@example.com',
            'aria-label': 'Your email address',
            'autocomplete': 'email',
        }),
        error_messages={
            'required': 'Please enter your email address.',
            'invalid': 'Please enter a valid email address.',
        },
    )

    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'What is this about?',
            'aria-label': 'Message subject',
        }),
        error_messages={
            'required': 'Please enter a subject.',
            'max_length': 'Subject cannot exceed 200 characters.',
        },
    )

    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Write your message here…',
            'aria-label': 'Your message',
            'rows': 6,
        }),
        error_messages={
            'required': 'Please enter your message.',
        },
    )
