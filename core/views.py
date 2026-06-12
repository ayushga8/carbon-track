"""Views for the core application — landing, about, and contact pages."""

import logging

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import ContactForm

logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    """Landing page with hero, stats, features, and call-to-action sections."""

    template_name = 'core/home.html'


class AboutView(TemplateView):
    """Static about page describing the CarbonTrack mission and team."""

    template_name = 'core/about.html'


class ContactView(FormView):
    """Contact page with a validated form that sends a success message."""

    template_name = 'core/contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('contact')

    def form_valid(self, form):
        """Process the valid contact form and display a success message."""
        # In production you would send an email here, e.g.:
        # send_mail(subject, message, from_email, [recipient])
        logger.info(
            "Contact form submitted — name=%s, email=%s, subject=%s",
            form.cleaned_data['name'],
            form.cleaned_data['email'],
            form.cleaned_data['subject'],
        )
        messages.success(
            self.request,
            "Thank you for reaching out! We'll get back to you within 24 hours.",
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        """Re-render the form with errors and display an error message."""
        messages.error(
            self.request,
            "There was a problem with your submission. Please correct the errors below.",
        )
        return super().form_invalid(form)
