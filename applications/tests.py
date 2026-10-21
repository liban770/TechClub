from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, UserRole
from applications.models import Application, ApplicationStatus, ReferralSource, NotificationLog
from members.models import MemberProfile, Skill
from events.models import Event, EventRegistration, EventStatus
from django.utils import timezone
from datetime import timedelta

class TechClubSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create Lead Organizer
        self.organizer = User.objects.create_user(
            username='organizer_test',
            email='lead@techclub.so',
            password='testpassword123',
            role=UserRole.ORGANIZER,
            is_staff=True,
            is_superuser=True
        )

        # Create Sample Member
        self.member_user = User.objects.create_user(
            username='member_test',
            email='member@techclub.so',
            password='memberpass123',
            role=UserRole.MEMBER
        )
        self.member_profile = MemberProfile.objects.create(
            user=self.member_user,
            full_name='Ahmed Builder',
            professional_title='Backend Go Developer',
            discipline='Software Engineering',
            is_mentor=True
        )

        # Create Sample Event with capacity 1
        now = timezone.now()
        self.event = Event.objects.create(
            title='Test Architecture Lab',
            description='Test event description',
            start_datetime=now + timedelta(days=2),
            end_datetime=now + timedelta(days=2, hours=2),
            venue='Innovation Hub Hall A',
            capacity=1,
            registration_deadline=now + timedelta(days=1),
            status=EventStatus.OPEN
        )

    def test_public_pages_load(self):
        resp_home = self.client.get(reverse('home'))
        self.assertEqual(resp_home.status_code, 200)
        self.assertContains(resp_home, "TechClub")
        self.assertContains(resp_home, "Where Young Tech Talent Meets Experience")

        resp_events = self.client.get(reverse('public_events'))
        self.assertEqual(resp_events.status_code, 200)

        resp_directory = self.client.get(reverse('member_directory'))
        self.assertEqual(resp_directory.status_code, 200)
        self.assertContains(resp_directory, "Ahmed Builder")

    def test_application_submission_and_approval_workflow(self):
        # 1. Submit application
        resp = self.client.post(reverse('apply'), {
            'full_name': 'Nimco Farhan',
            'email': 'nimco@applicant.so',
            'phone': '+252 63 4400000',
            'city': 'Hargeisa',
            'current_role': 'Frontend Developer',
            'professional_category': 'Software Engineering',
            'organization': 'Telesom Tech',
            'experience_level': 'Junior (1-2y)',
            'skills': 'React, Tailwind, TypeScript',
            'profile_summary': 'Excited to join TechClub and build with the community.',
            'interests': ['Professional networking', 'Finding a mentor'],
            'referral_source': ReferralSource.WHATSAPP,
        })
        self.assertEqual(resp.status_code, 302)

        # Check application created with status PENDING
        app = Application.objects.get(email='nimco@applicant.so')
        self.assertEqual(app.status, ApplicationStatus.PENDING)
        self.assertEqual(app.referral_source, ReferralSource.WHATSAPP)

        # Check confirmation notification logged
        log = NotificationLog.objects.filter(recipient_email='nimco@applicant.so').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.message_type, 'APPLICATION_RECEIVED')

        # 2. Organizer approves application
        self.client.login(username='lead@techclub.so', password='testpassword123')
        action_resp = self.client.post(reverse('admin_application_action', args=[app.id]), {
            'action': 'APPROVE',
            'notes': 'Great portfolio, approved for Cohort #2!'
        })
        self.assertEqual(action_resp.status_code, 302)

        app.refresh_from_db()
        self.assertEqual(app.status, ApplicationStatus.APPROVED)

        # Check User account automatically created and activation token generated
        new_user = User.objects.get(email='nimco@applicant.so')
        self.assertEqual(new_user.role, UserRole.MEMBER)
        self.assertTrue(new_user.must_set_password)
        self.assertIsNotNone(new_user.activation_token)

        # Check MemberProfile automatically created
        new_profile = MemberProfile.objects.get(user=new_user)
        self.assertEqual(new_profile.full_name, 'Nimco Farhan')

        # 3. Applicant uses activation link to set password
        token = new_user.activation_token
        self.client.logout()
        activate_resp = self.client.post(reverse('activate_account', args=[token]), {
            'password': 'newpassword123',
            'confirm_password': 'newpassword123',
        })
        self.assertEqual(activate_resp.status_code, 302)

        new_user.refresh_from_db()
        self.assertFalse(new_user.must_set_password)
        self.assertIsNone(new_user.activation_token)

    def test_event_capacity_and_attendance(self):
        # First registration takes the 1 seat
        resp1 = self.client.post(reverse('event_register', args=[self.event.id]), {
            'name': 'Participant 1',
            'email': 'p1@example.com',
            'phone': '123'
        })
        self.assertEqual(resp1.status_code, 302)
        reg1 = EventRegistration.objects.get(attendee_email='p1@example.com')
        self.assertEqual(reg1.status, 'REGISTERED')

        # Second registration gets auto-waitlisted because capacity=1
        resp2 = self.client.post(reverse('event_register', args=[self.event.id]), {
            'name': 'Participant 2',
            'email': 'p2@example.com',
            'phone': '456'
        })
        self.assertEqual(resp2.status_code, 302)
        reg2 = EventRegistration.objects.get(attendee_email='p2@example.com')
        self.assertEqual(reg2.status, 'WAITLISTED')

        # Organizer marks attendance
        self.client.login(username='lead@techclub.so', password='testpassword123')
        att_resp = self.client.post(reverse('admin_attendance_toggle', args=[reg1.id]), {
            'status': 'ATTENDED'
        })
        self.assertEqual(att_resp.status_code, 302)
        reg1.refresh_from_db()
        self.assertEqual(reg1.attendance_status, 'ATTENDED')
