"""
Tests for the core app.

~15 tests covering home, about, contact pages, and context processor.
"""

from django.test import TestCase, Client
from django.urls import reverse

from .forms import ContactForm


# ============================================================
# HOME PAGE TESTS
# ============================================================

class TestHomeView(TestCase):
    """Test home page."""

    def setUp(self):
        self.client = Client()

    def test_home_page_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_home_page_uses_correct_template(self):
        response = self.client.get(reverse('home'))
        self.assertTemplateUsed(response, 'core/home.html')

    def test_home_page_contains_cta(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Get Started')

    def test_home_page_contains_brand(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'CarbonTrack')


# ============================================================
# ABOUT PAGE TESTS
# ============================================================

class TestAboutView(TestCase):
    """Test about page."""

    def setUp(self):
        self.client = Client()

    def test_about_page_loads(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)

    def test_about_page_uses_correct_template(self):
        response = self.client.get(reverse('about'))
        self.assertTemplateUsed(response, 'core/about.html')


# ============================================================
# CONTACT PAGE TESTS
# ============================================================

class TestContactView(TestCase):
    """Test contact page and form."""

    def setUp(self):
        self.client = Client()

    def test_contact_page_loads(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)

    def test_contact_page_contains_form(self):
        response = self.client.get(reverse('contact'))
        self.assertIn('form', response.context)


# ============================================================
# CONTACT FORM TESTS
# ============================================================

class TestContactForm(TestCase):
    """Test contact form validation."""

    def get_valid_data(self):
        return {
            'name': 'John Doe',
            'email': 'john@example.com',
            'subject': 'Test Subject',
            'message': 'Hello, this is a test message.',
        }

    def test_valid_form(self):
        form = ContactForm(data=self.get_valid_data())
        self.assertTrue(form.is_valid())

    def test_missing_name_rejected(self):
        data = self.get_valid_data()
        data['name'] = ''
        form = ContactForm(data=data)
        self.assertFalse(form.is_valid())

    def test_missing_email_rejected(self):
        data = self.get_valid_data()
        data['email'] = ''
        form = ContactForm(data=data)
        self.assertFalse(form.is_valid())

    def test_invalid_email_rejected(self):
        data = self.get_valid_data()
        data['email'] = 'not-an-email'
        form = ContactForm(data=data)
        self.assertFalse(form.is_valid())

    def test_missing_message_rejected(self):
        data = self.get_valid_data()
        data['message'] = ''
        form = ContactForm(data=data)
        self.assertFalse(form.is_valid())

    def test_missing_subject_rejected(self):
        data = self.get_valid_data()
        data['subject'] = ''
        form = ContactForm(data=data)
        self.assertFalse(form.is_valid())


# ============================================================
# CONTEXT PROCESSOR TESTS
# ============================================================

class TestFirebaseContextProcessor(TestCase):
    """Test Firebase config context processor."""

    def setUp(self):
        self.client = Client()

    def test_firebase_keys_in_context(self):
        response = self.client.get(reverse('home'))
        self.assertIn('firebase_api_key', response.context)
        self.assertIn('firebase_auth_domain', response.context)
        self.assertIn('firebase_project_id', response.context)
