from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import User, UserRole, InAppNotification, UserActivity, log_activity, notify_user
from applications.models import NotificationLog

class AccountsAndOTPTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Create Organizer
        self.organizer = User.objects.create_user(
            username='organizer@techclub.so',
            email='organizer@techclub.so',
            password='adminpassword123',
            first_name='Jamaal',
            last_name='Maxamed',
            role=UserRole.ORGANIZER,
            is_staff=True,
            is_superuser=True
        )
        # Create Member
        self.member = User.objects.create_user(
            username='member@telesom.so',
            email='member@telesom.so',
            password='oldpassword123',
            first_name='Guled',
            last_name='Abdi',
            role=UserRole.MEMBER
        )

    def test_otp_model_methods(self):
        """Test OTP generation, verification, and expiration logic."""
        code = self.member.generate_otp()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        self.assertEqual(self.member.otp_code, code)

        # Test valid verification
        self.assertTrue(self.member.verify_otp(code))

        # Test invalid verification
        self.assertFalse(self.member.verify_otp('000000'))

        # Test expired OTP (> 15 minutes)
        self.member.otp_created_at = timezone.now() - timedelta(minutes=16)
        self.member.save()
        self.assertFalse(self.member.verify_otp(code))

        # Test clear OTP
        self.member.clear_otp()
        self.assertIsNone(self.member.otp_code)
        self.assertIsNone(self.member.otp_created_at)

    def test_forgot_password_and_otp_reset_flow(self):
        """Test end-to-end forgot password OTP recovery."""
        # 1. Request OTP
        resp = self.client.post(reverse('forgot_password'), {'email': 'member@telesom.so'}, follow=True)
        self.assertEqual(resp.status_code, 200)

        self.member.refresh_from_db()
        otp = self.member.otp_code
        self.assertIsNotNone(otp)

        # Check NotificationLog was created
        log_entry = NotificationLog.objects.filter(recipient_email='member@telesom.so', message_type='PASSWORD_RESET_OTP').first()
        self.assertIsNotNone(log_entry)
        self.assertIn(otp, log_entry.content)

        # 2. Verify OTP and set new password
        reset_resp = self.client.post(reverse('verify_otp'), {
            'email': 'member@telesom.so',
            'otp_code': otp,
            'new_password': 'BrandNewPassword2026!',
            'confirm_password': 'BrandNewPassword2026!'
        }, follow=True)
        self.assertEqual(reset_resp.status_code, 200)

        # Verify password actually changed
        self.member.refresh_from_db()
        self.assertTrue(self.member.check_password('BrandNewPassword2026!'))
        self.assertIsNone(self.member.otp_code)

        # Check UserActivity logged
        activity = UserActivity.objects.filter(user=self.member, activity_type='PASSWORD_RESET_SUCCESS').first()
        self.assertIsNotNone(activity)

    def test_admin_user_management(self):
        """Test organizer viewing users, toggling active status, and changing roles."""
        self.client.login(username='organizer@techclub.so', password='adminpassword123')

        # 1. Users list view
        resp = self.client.get(reverse('admin_users'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Guled Abdi')

        # 2. Toggle active status
        self.assertTrue(self.member.is_active)
        toggle_resp = self.client.post(reverse('admin_user_toggle_status', kwargs={'user_id': self.member.id}), follow=True)
        self.assertEqual(toggle_resp.status_code, 200)
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)

        # Reactivate
        self.client.post(reverse('admin_user_toggle_status', kwargs={'user_id': self.member.id}), follow=True)
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)

        # 3. Change Role: Member -> Organizer
        self.client.post(reverse('admin_user_change_role', kwargs={'user_id': self.member.id}), {'new_role': UserRole.ORGANIZER}, follow=True)
        self.member.refresh_from_db()
        self.assertEqual(self.member.role, UserRole.ORGANIZER)
        self.assertTrue(self.member.is_staff)

        # 4. Admin Reset Password
        self.client.post(reverse('admin_user_reset_password', kwargs={'user_id': self.member.id}), {'new_password': 'AdminAssignedPass99!'}, follow=True)
        self.member.refresh_from_db()
        self.assertTrue(self.member.check_password('AdminAssignedPass99!'))

    def test_in_app_notifications(self):
        """Test notification creation, context processor delivery, and marking read."""
        notif = notify_user(self.member, "System Notice", "Welcome to TechClub notifications", "SUCCESS")
        self.assertIsNotNone(notif)
        self.assertFalse(notif.is_read)

        self.client.login(username='member@telesom.so', password='oldpassword123')

        # Mark single notification as read
        resp = self.client.get(reverse('mark_notification_read', kwargs={'pk': notif.id}), follow=True)
        self.assertEqual(resp.status_code, 200)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

        # Create another notification and test mark all read
        notify_user(self.member, "Notice 2", "Another message", "INFO")
        self.client.post(reverse('mark_all_notifications_read'), follow=True)
        unread = InAppNotification.objects.filter(recipient=self.member, is_read=False).count()
        self.assertEqual(unread, 0)
