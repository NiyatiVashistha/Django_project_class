from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.models import OTPVerification

User = get_user_model()

class AccountsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@test.com", password="password123")
        self.user.is_active = False
        self.user.save()

    def test_otp_generation(self):
        otp, created = OTPVerification.objects.get_or_create(user=self.user)
        otp.generate_otp()
        self.assertIsNotNone(otp.otp_code)
        self.assertEqual(len(otp.otp_code), 6)
        self.assertFalse(otp.is_verified)
        self.assertTrue(otp.is_valid())

    def test_registration_creates_otp(self):
        response = self.client.post(reverse("accounts:register"), {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "password123",
            "password_confirmation": "password123"
        })
        self.assertTrue(User.objects.filter(username="newuser").exists())
        new_user = User.objects.get(username="newuser")
        self.assertFalse(new_user.is_active)
        self.assertTrue(OTPVerification.objects.filter(user=new_user).exists())

    def test_otp_verification(self):
        otp, _ = OTPVerification.objects.get_or_create(user=self.user)
        otp.generate_otp()
        
        session = self.client.session
        session['pre_otp_user_id'] = self.user.id
        session.save()

        response = self.client.post(reverse("accounts:otp_verify"), {
            "otp_code": otp.otp_code
        })
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        otp.refresh_from_db()
        self.assertTrue(otp.is_verified)
