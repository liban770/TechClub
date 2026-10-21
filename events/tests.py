from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from datetime import timedelta
from techclub_core.validators import validate_uploaded_document
from members.models import MemberProfile
from .models import (
    Event, EventMode, EventStatus, EventCategory, EventAudienceRole,
    EventRegistration, EventResource, EventResourceType, ResourceAccessRole,
    EventFeedback
)

User = get_user_model()

class OnlineEventsAndResourcesTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username='organizer1',
            email='organizer@techclub.so',
            password='Password123!',
            is_staff=True
        )
        self.member_user = User.objects.create_user(
            username='member1',
            email='member@techclub.so',
            password='Password123!'
        )

        now = timezone.now()
        self.online_event = Event.objects.create(
            title='Cloud Architecture Masterclass',
            description='Hands-on cloud architecture workshop.',
            category=EventCategory.WORKSHOP,
            event_mode=EventMode.ONLINE,
            meeting_url='https://zoom.us/j/9876543210',
            meeting_platform='Zoom',
            meeting_passcode='CLOUD2026',
            is_live_now=False,
            start_datetime=now + timedelta(days=2),
            end_datetime=now + timedelta(days=2, hours=3),
            venue='Zoom Virtual Room 1',
            capacity=100,
            registration_deadline=now + timedelta(days=2),
            created_by=self.organizer
        )

    def test_online_event_properties(self):
        self.assertTrue(self.online_event.is_online)
        self.assertEqual(self.online_event.meeting_platform, 'Zoom')
        self.assertEqual(self.online_event.meeting_passcode, 'CLOUD2026')

    def test_document_validation_whitelist_and_blacklist(self):
        # Whitelisted: PDF, PPTX, XLSX
        valid_pdf = SimpleUploadedFile("slides.pdf", b"%PDF-1.4 test content", content_type="application/pdf")
        validate_uploaded_document(valid_pdf)

        valid_xlsx = SimpleUploadedFile("data.xlsx", b"excel mock binary content", content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        validate_uploaded_document(valid_xlsx)

        # Blacklisted: .exe, .sh, .py, .php
        dangerous_exe = SimpleUploadedFile("trojan.exe", b"binary executable", content_type="application/x-msdownload")
        with self.assertRaises(ValidationError):
            validate_uploaded_document(dangerous_exe)

        dangerous_py = SimpleUploadedFile("script.py", b"import os; os.system('calc')", content_type="text/x-python")
        with self.assertRaises(ValidationError):
            validate_uploaded_document(dangerous_py)

    def test_event_resource_creation_and_auto_detection(self):
        test_file = SimpleUploadedFile("architecture_diagrams.pdf", b"%PDF-1.4 " + (b"0" * 2048), content_type="application/pdf")
        resource = EventResource.objects.create(
            event=self.online_event,
            title='Architecture Diagrams & Cheatsheet',
            file=test_file,
            created_by=self.organizer
        )
        self.assertEqual(resource.resource_type, EventResourceType.PDF)
        self.assertEqual(resource.file_extension, '.pdf')
        self.assertIn('KB', resource.formatted_file_size)

    def test_ticket_generation_and_qr_code(self):
        registration = EventRegistration.objects.create(
            event=self.online_event,
            attendee_name='Farhan Ahmed',
            attendee_email='farhan@somalia.so',
            attendee_phone='+252634441122',
            status='REGISTERED',
            attendance_status='PENDING'
        )
        self.assertTrue(registration.ticket_code.startswith('TC-EVT-'))
        self.assertIsNotNone(registration.qr_code_image)
        # Certificate should not be issued yet
        self.assertIsNone(registration.certificate_id)

    def test_ticket_scan_checkin_issues_official_certificate(self):
        registration = EventRegistration.objects.create(
            event=self.online_event,
            attendee_name='Amina Hersi',
            attendee_email='amina@techclub.so',
            status='REGISTERED',
            attendance_status='PENDING'
        )
        ticket_code = registration.ticket_code

        client = Client()
        client.force_login(self.organizer)

        # Scan ticket via API
        response = client.post('/admin-ops/scan-ticket/', {'ticket_code': ticket_code}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIsNotNone(data['certificate_id'])
        self.assertTrue(data['certificate_id'].startswith('TC-CERT-'))

        # Verify registration record updated
        registration.refresh_from_db()
        self.assertEqual(registration.attendance_status, 'ATTENDED')
        self.assertEqual(registration.certificate_id, data['certificate_id'])
        self.assertIsNotNone(registration.certificate_issued_at)

        # Verify public certificate verification view works
        cert_res = client.get(f'/verify/{registration.certificate_id}/')
        self.assertEqual(cert_res.status_code, 200)
        self.assertContains(cert_res, 'Amina Hersi')
        self.assertContains(cert_res, self.online_event.title)

    def test_automatic_online_join_verifies_attendance_and_issues_certificate(self):
        registration = EventRegistration.objects.create(
            event=self.online_event,
            attendee_name='Khadar Jama',
            attendee_email='khadar@techclub.so',
            status='REGISTERED',
            attendance_status='PENDING'
        )
        self.assertIsNone(registration.certificate_id)

        client = Client()
        # Click "Join Live Class"
        response = client.get(f'/events/ticket/{registration.ticket_code}/join-live/')
        # Should redirect to Zoom meeting url
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.online_event.meeting_url)

        # Verify attendance marked and certificate automatically issued
        registration.refresh_from_db()
        self.assertEqual(registration.attendance_status, 'ATTENDED')
        self.assertIsNotNone(registration.certificate_id)
        self.assertTrue(registration.certificate_id.startswith('TC-CERT-'))
        self.assertIsNotNone(registration.certificate_issued_at)

    def test_community_member_vs_guest_differentiation(self):
        # 1. Guest attendee (no member profile)
        guest_reg = EventRegistration.objects.create(
            event=self.online_event,
            attendee_name='Guest Person',
            attendee_email='guest@example.com',
            status='REGISTERED',
            attendance_status='ATTENDED'
        )
        self.assertFalse(guest_reg.is_community_member)
        self.assertEqual(guest_reg.attendee_type_label, "Public Guest")
        self.assertEqual(guest_reg.pass_badge_title, "TechClub Public Guest Pass")

        # 2. Verified Community Member
        member_profile = MemberProfile.objects.create(
            user=self.member_user,
            full_name='Liban Member',
            cohort='Cohort Beta'
        )
        member_reg = EventRegistration.objects.create(
            event=self.online_event,
            member=member_profile,
            attendee_name='Liban Member',
            attendee_email='member@techclub.so',
            status='REGISTERED',
            attendance_status='ATTENDED'
        )
        self.assertTrue(member_reg.is_community_member)
        self.assertEqual(member_reg.attendee_type_label, "Community Member")
        self.assertIn("Cohort Beta", member_reg.pass_badge_title)

        # 3. Members-only resource check
        test_file = SimpleUploadedFile("solutions.pdf", b"%PDF-1.4 solution content", content_type="application/pdf")
        exclusive_res = EventResource.objects.create(
            event=self.online_event,
            title='Full Code Solutions',
            file=test_file,
            is_members_only=True,
            created_by=self.organizer
        )
        self.assertTrue(exclusive_res.is_members_only)

        client = Client()
        # Guest views ticket -> sees guest badge and locked member download
        guest_ticket_resp = client.get(f'/events/ticket/{guest_reg.ticket_code}/')
        self.assertEqual(guest_ticket_resp.status_code, 200)
        self.assertContains(guest_ticket_resp, 'Public Guest Pass')
        self.assertContains(guest_ticket_resp, 'Apply to Unlock')

        # Member views ticket -> sees member pass badge
        member_ticket_resp = client.get(f'/events/ticket/{member_reg.ticket_code}/')
        self.assertEqual(member_ticket_resp.status_code, 200)
        self.assertContains(member_ticket_resp, 'TechClub Member Pass')
        self.assertContains(member_ticket_resp, 'Members')

    def test_role_dropdowns_in_courses_and_materials(self):
        # 1. Test Event audience_role
        now = timezone.now()
        members_only_event = Event.objects.create(
            title='Exclusive Founders Circle',
            description='Private invite-only founder roundtable.',
            category=EventCategory.FIRESIDE,
            audience_role=EventAudienceRole.MEMBER,
            start_datetime=now + timedelta(days=5),
            end_datetime=now + timedelta(days=5, hours=2),
            venue='Hub Private Lounge',
            capacity=20,
            registration_deadline=now + timedelta(days=5),
            created_by=self.organizer
        )
        self.assertEqual(members_only_event.audience_role, EventAudienceRole.MEMBER)
        self.assertEqual(members_only_event.audience_badge_info['label'], 'Members Only')

        # 2. Test Public Events list role filter
        client = Client()
        resp_all = client.get('/events/')
        self.assertEqual(resp_all.status_code, 200)
        self.assertContains(resp_all, 'Cloud Architecture Masterclass')
        self.assertContains(resp_all, 'Exclusive Founders Circle')

        resp_members_only = client.get('/events/?role=MEMBER')
        self.assertEqual(resp_members_only.status_code, 200)
        self.assertContains(resp_members_only, 'Exclusive Founders Circle')
        self.assertNotContains(resp_members_only, 'Cloud Architecture Masterclass')

        resp_public_only = client.get('/events/?role=PUBLIC')
        self.assertEqual(resp_public_only.status_code, 200)
        self.assertContains(resp_public_only, 'Cloud Architecture Masterclass')
        self.assertNotContains(resp_public_only, 'Exclusive Founders Circle')

        # 3. Test Material access roles & permissions
        mentor_user = User.objects.create_user(
            username='mentor1',
            email='mentor@techclub.so',
            password='Password123!'
        )
        MemberProfile.objects.create(
            user=mentor_user,
            full_name='Mentor Lead',
            is_mentor=True
        )

        member_profile = MemberProfile.objects.filter(user=self.member_user).first()
        if not member_profile:
            member_profile = MemberProfile.objects.create(
                user=self.member_user,
                full_name='Liban Regular Member',
                is_mentor=False
            )

        pdf_content = b"%PDF-1.4 test content"
        pub_file = SimpleUploadedFile("guide.pdf", pdf_content, content_type="application/pdf")
        member_file = SimpleUploadedFile("workbook.pdf", pdf_content, content_type="application/pdf")
        mentor_file = SimpleUploadedFile("answer_key.pdf", pdf_content, content_type="application/pdf")
        org_file = SimpleUploadedFile("runbook.pdf", pdf_content, content_type="application/pdf")

        res_pub = EventResource.objects.create(
            event=self.online_event, title='Public Guide', file=pub_file,
            access_role=ResourceAccessRole.PUBLIC, created_by=self.organizer
        )
        res_member = EventResource.objects.create(
            event=self.online_event, title='Member Workbook', file=member_file,
            access_role=ResourceAccessRole.MEMBER, created_by=self.organizer
        )
        res_mentor = EventResource.objects.create(
            event=self.online_event, title='Mentor Answer Key', file=mentor_file,
            access_role=ResourceAccessRole.MENTOR, created_by=self.organizer
        )
        res_org = EventResource.objects.create(
            event=self.online_event, title='Organizer Runbook', file=org_file,
            access_role=ResourceAccessRole.ORGANIZER, created_by=self.organizer
        )

        # Public guest can only access public resource
        self.assertTrue(res_pub.can_user_download(user=None, is_community_member=False))
        self.assertFalse(res_member.can_user_download(user=None, is_community_member=False))
        self.assertFalse(res_mentor.can_user_download(user=None, is_community_member=False))
        self.assertFalse(res_org.can_user_download(user=None, is_community_member=False))

        # Member can access public + member resources
        self.assertTrue(res_pub.can_user_download(user=self.member_user, is_community_member=True))
        self.assertTrue(res_member.can_user_download(user=self.member_user, is_community_member=True))
        self.assertFalse(res_mentor.can_user_download(user=self.member_user, is_community_member=True))
        self.assertFalse(res_org.can_user_download(user=self.member_user, is_community_member=True))

        # Mentor can access public + member + mentor resources
        self.assertTrue(res_pub.can_user_download(user=mentor_user, is_community_member=True))
        self.assertTrue(res_member.can_user_download(user=mentor_user, is_community_member=True))
        self.assertTrue(res_mentor.can_user_download(user=mentor_user, is_community_member=True))
        self.assertFalse(res_org.can_user_download(user=mentor_user, is_community_member=True))

        # Organizer can access all resources
        self.assertTrue(res_pub.can_user_download(user=self.organizer, is_community_member=True))
        self.assertTrue(res_member.can_user_download(user=self.organizer, is_community_member=True))
        self.assertTrue(res_mentor.can_user_download(user=self.organizer, is_community_member=True))
        self.assertTrue(res_org.can_user_download(user=self.organizer, is_community_member=True))

        # 4. Test Organizer switching resource role via API/endpoint
        client.force_login(self.organizer)
        resp = client.post(f'/admin-ops/resources/{res_pub.id}/role/', {'access_role': 'MENTOR'})
        self.assertEqual(resp.status_code, 302)
        res_pub.refresh_from_db()
        self.assertEqual(res_pub.access_role, ResourceAccessRole.MENTOR)

    def test_resource_download_counter_and_analytics(self):
        """Test download tracking, counter incrementation, ticket validation, and analytics."""
        client = Client()
        pdf_content = b"%PDF-1.4 test download analytics content"
        test_file = SimpleUploadedFile("analytics_guide.pdf", pdf_content, content_type="application/pdf")
        
        resource = EventResource.objects.create(
            event=self.online_event,
            title='Analytics Test Guide',
            file=test_file,
            access_role=ResourceAccessRole.PUBLIC,
            created_by=self.organizer
        )
        self.assertEqual(resource.download_count, 0)

        # 1. Anonymous visitor downloads public file
        download_url = f'/events/resources/{resource.id}/download/'
        resp = client.get(download_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('attachment', resp.headers.get('Content-Disposition', ''))
        resource.refresh_from_db()
        self.assertEqual(resource.download_count, 1)

        # 2. Second download increments counter to 2
        resp2 = client.get(download_url)
        self.assertEqual(resp2.status_code, 200)
        resource.refresh_from_db()
        self.assertEqual(resource.download_count, 2)

        # 3. Member-restricted resource download control
        member_file = SimpleUploadedFile("member_secrets.pdf", pdf_content, content_type="application/pdf")
        member_res = EventResource.objects.create(
            event=self.online_event,
            title='Member Exclusive Cheatsheet',
            file=member_file,
            access_role=ResourceAccessRole.MEMBER,
            created_by=self.organizer
        )
        self.assertEqual(member_res.download_count, 0)

        # Anonymous visitor without ticket is redirected to apply
        unauth_resp = client.get(f'/events/resources/{member_res.id}/download/')
        self.assertEqual(unauth_resp.status_code, 302)
        member_res.refresh_from_db()
        self.assertEqual(member_res.download_count, 0)

        # Create registration with member profile
        member_profile = MemberProfile.objects.filter(user=self.member_user).first()
        if not member_profile:
            member_profile = MemberProfile.objects.create(
                user=self.member_user,
                full_name='Liban Member',
                is_mentor=False
            )
        reg = EventRegistration.objects.create(
            event=self.online_event,
            member=member_profile,
            attendee_name='Liban Member',
            attendee_email='liban@techclub.so',
            ticket_code='TC-MEMBER-TEST-01'
        )

        # Guest with verified member ticket can download via ticket query param
        ticket_download_resp = client.get(f'/events/resources/{member_res.id}/download/?ticket={reg.ticket_code}')
        self.assertEqual(ticket_download_resp.status_code, 200)
        member_res.refresh_from_db()
        self.assertEqual(member_res.download_count, 1)

        # Logged-in member can download directly
        client.force_login(self.member_user)
        logged_in_resp = client.get(f'/events/resources/{member_res.id}/download/')
        self.assertEqual(logged_in_resp.status_code, 200)
        member_res.refresh_from_db()
        self.assertEqual(member_res.download_count, 2)

    def test_calendar_generation_and_ics_download(self):
        """Feature 1: Test Google Calendar URL generation and .ics download endpoint."""
        client = Client()
        
        # Test Google Calendar URL property on Event
        gcal_url = self.online_event.google_calendar_url
        self.assertIn("calendar.google.com/calendar/render", gcal_url)
        self.assertIn("action=TEMPLATE", gcal_url)

        # Test .ics calendar file download endpoint
        ics_url = f"/events/{self.online_event.id}/calendar.ics"
        resp = client.get(ics_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/calendar", resp.headers.get("Content-Type", "") or resp.get("Content-Type", ""))
        self.assertIn("attachment", resp.headers.get("Content-Disposition", "") or resp.get("Content-Disposition", ""))
        content = resp.content.decode("utf-8")
        self.assertIn("BEGIN:VCALENDAR", content)
        self.assertIn("BEGIN:VEVENT", content)
        self.assertIn(f"SUMMARY:{self.online_event.title}", content)
        self.assertIn("END:VCALENDAR", content)

    def test_self_service_cancellation_and_waitlist_promotion(self):
        """Feature 2: Test attendee RSVP cancellation and automated Priority Waitlist promotion."""
        client = Client()

        # Set capacity to 1 for precise waitlist test
        self.online_event.capacity = 1
        self.online_event.status = EventStatus.OPEN
        self.online_event.save()

        # 1. First attendee registers and gets confirmed
        reg_confirmed = EventRegistration.objects.create(
            event=self.online_event,
            attendee_name="Attendee Alpha",
            attendee_email="alpha@domain.so",
            status="REGISTERED"
        )

        # 2. Second attendee is placed on Priority Waitlist
        reg_waitlisted = EventRegistration.objects.create(
            event=self.online_event,
            attendee_name="Attendee Beta",
            attendee_email="beta@domain.so",
            status="WAITLISTED"
        )
        self.assertEqual(reg_waitlisted.status, "WAITLISTED")

        # 3. First attendee cancels their RSVP
        cancel_url = f"/events/ticket/{reg_confirmed.ticket_code}/cancel/"
        resp = client.post(cancel_url)
        self.assertEqual(resp.status_code, 302)

        reg_confirmed.refresh_from_db()
        self.assertEqual(reg_confirmed.status, "CANCELLED")

        # 4. Waitlisted attendee must be automatically promoted to REGISTERED
        reg_waitlisted.refresh_from_db()
        self.assertEqual(reg_waitlisted.status, "REGISTERED")

        # Attended attendee cannot cancel
        reg_waitlisted.attendance_status = "ATTENDED"
        reg_waitlisted.save()
        bad_cancel_resp = client.post(f"/events/ticket/{reg_waitlisted.ticket_code}/cancel/")
        self.assertEqual(bad_cancel_resp.status_code, 302)
        reg_waitlisted.refresh_from_db()
        self.assertEqual(reg_waitlisted.status, "REGISTERED")

    def test_attendee_feedback_rating_system(self):
        """Feature 4: Test attendee satisfaction rating submission and aggregate calculation."""
        client = Client()

        reg = EventRegistration.objects.create(
            event=self.online_event,
            attendee_name="Reviewer User",
            attendee_email="reviewer@domain.so",
            status="REGISTERED",
            attendance_status="PENDING"
        )

        feedback_url = f"/events/ticket/{reg.ticket_code}/feedback/"

        # 1. Unchecked attendee cannot submit feedback
        unauth_resp = client.post(feedback_url, {"rating": 5, "feedback_text": "Great session!"})
        self.assertEqual(unauth_resp.status_code, 302)
        self.assertEqual(EventFeedback.objects.filter(registration=reg).count(), 0)

        # 2. Once verified as ATTENDED, attendee can submit rating & review
        reg.attendance_status = "ATTENDED"
        reg.save()

        submit_resp = client.post(feedback_url, {"rating": 5, "feedback_text": "Incredible architecture insights!"})
        self.assertEqual(submit_resp.status_code, 302)

        fb = EventFeedback.objects.filter(registration=reg).first()
        self.assertIsNotNone(fb)
        self.assertEqual(fb.rating, 5)
        self.assertEqual(fb.feedback_text, "Incredible architecture insights!")

        # 3. Verify Event average rating property
        self.online_event.refresh_from_db()
        self.assertEqual(self.online_event.average_rating, 5.0)
        self.assertEqual(self.online_event.feedback_count, 1)



