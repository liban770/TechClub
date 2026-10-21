from django.db import models
from django.conf import settings
from django.utils import timezone
from members.models import MemberProfile

class EventCategory(models.TextChoices):
    MEETUP = 'Technical Meetup', 'Technical Meetup'
    LAB = 'Architecture Lab', 'Architecture Lab'
    FIRESIDE = 'Fireside Panel', 'Fireside Panel'
    WORKSHOP = 'Hands-on Workshop', 'Hands-on Workshop'
    HACKATHON = 'Hackathon & Build Sprint', 'Hackathon & Build Sprint'

class EventStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    OPEN = 'OPEN', 'Open for Registration'
    FULL = 'FULL', 'Full (Waitlist Only)'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'

class EventMode(models.TextChoices):
    IN_PERSON = 'IN_PERSON', 'In-Person Gathering'
    ONLINE = 'ONLINE', 'Online Live Session (Zoom / Meet)'
    HYBRID = 'HYBRID', 'Hybrid (In-Person & Online)'

class EventAudienceRole(models.TextChoices):
    PUBLIC = 'PUBLIC', 'Open to All (Guests & Members)'
    MEMBER = 'MEMBER', 'TechClub Members Only'
    MENTOR = 'MENTOR', 'Mentors & Instructors Only'

class Event(models.Model):
    title = models.CharField(max_length=200, verbose_name="Event Title")
    description = models.TextField(verbose_name="Event Description")
    category = models.CharField(
        max_length=50,
        choices=EventCategory.choices,
        default=EventCategory.MEETUP
    )
    audience_role = models.CharField(
        max_length=20,
        choices=EventAudienceRole.choices,
        default=EventAudienceRole.PUBLIC,
        verbose_name="Target Role / Audience"
    )
    event_mode = models.CharField(
        max_length=20,
        choices=EventMode.choices,
        default=EventMode.IN_PERSON,
        verbose_name="Delivery Mode"
    )
    meeting_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="Live Meeting URL (Zoom / Meet)")
    meeting_platform = models.CharField(max_length=50, blank=True, default="Zoom", verbose_name="Meeting Platform")
    meeting_passcode = models.CharField(max_length=100, blank=True, null=True, verbose_name="Meeting Passcode / ID")
    is_live_now = models.BooleanField(default=False, verbose_name="Live Session Active Now")

    start_datetime = models.DateTimeField(verbose_name="Start Date & Time")
    end_datetime = models.DateTimeField(verbose_name="End Date & Time")
    venue = models.CharField(max_length=200, default="Hargeisa, Somaliland")
    capacity = models.PositiveIntegerField(default=50, verbose_name="Maximum Capacity")
    registration_deadline = models.DateTimeField(verbose_name="Registration Deadline")
    cover_image_url = models.CharField(max_length=500, blank=True)
    cover_image = models.ImageField(upload_to='events/covers/', blank=True, null=True, verbose_name="Cover Image Upload")
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.OPEN
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_datetime']

    def __str__(self):
        return f"{self.title} ({self.start_datetime.strftime('%b %d, %Y')})"

    @property
    def display_cover_image(self):
        if self.cover_image:
            return self.cover_image.url
        if self.cover_image_url:
            return self.cover_image_url
        return "/static/images/hub-hero.png"

    @property
    def registered_count(self):
        return self.registrations.filter(status='REGISTERED').count()

    @property
    def waitlisted_count(self):
        return self.registrations.filter(status='WAITLISTED').count()

    @property
    def attended_count(self):
        return self.registrations.filter(attendance_status='ATTENDED').count()

    @property
    def available_seats(self):
        return max(0, self.capacity - self.registered_count)

    @property
    def is_full(self):
        return self.registered_count >= self.capacity

    @property
    def is_past(self):
        return self.end_datetime < timezone.now()

    @property
    def is_online(self):
        return self.event_mode in (EventMode.ONLINE, EventMode.HYBRID)

    @property
    def audience_badge_info(self):
        if self.audience_role == EventAudienceRole.MENTOR:
            return {
                'label': 'Mentors Only',
                'icon': 'stars',
                'color': 'bg-purple-100 text-purple-900 border-purple-300',
            }
        elif self.audience_role == EventAudienceRole.MEMBER:
            return {
                'label': 'Members Only',
                'icon': 'workspace_premium',
                'color': 'bg-amber-100 text-amber-900 border-amber-300',
            }
        return {
            'label': 'Open to All',
            'icon': 'public',
            'color': 'bg-emerald-100 text-emerald-900 border-emerald-300',
        }

    @property
    def google_calendar_url(self):
        """Generate direct Google Calendar Add-Event URL."""
        import urllib.parse
        import datetime
        start_utc = self.start_datetime.astimezone(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        end_utc = self.end_datetime.astimezone(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        details = self.description[:500] if self.description else ""
        if self.is_online and self.meeting_url:
            details += f"\n\nLive Stream: {self.meeting_url}"
            if self.meeting_passcode:
                details += f"\nPasscode / PIN: {self.meeting_passcode}"
        params = {
            'action': 'TEMPLATE',
            'text': self.title,
            'dates': f"{start_utc}/{end_utc}",
            'details': details,
            'location': self.venue if not self.is_online else (self.meeting_url or self.venue),
        }
        return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"

    @property
    def average_rating(self):
        from django.db.models import Avg
        avg = self.feedbacks.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else None

    @property
    def feedback_count(self):
        return self.feedbacks.count()

import secrets
import urllib.parse
from io import BytesIO
from django.core.files.base import ContentFile
import qrcode

class EventRegistration(models.Model):
    REGISTRATION_STATUS = (
        ('REGISTERED', 'Confirmed Registration'),
        ('WAITLISTED', 'Waitlisted'),
        ('CANCELLED', 'Cancelled'),
    )

    ATTENDANCE_STATUS = (
        ('PENDING', 'Pending Attendance'),
        ('ATTENDED', 'Attended'),
        ('ABSENT', 'Absent'),
    )

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    member = models.ForeignKey(MemberProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='event_registrations')
    attendee_name = models.CharField(max_length=150)
    attendee_email = models.EmailField()
    attendee_phone = models.CharField(max_length=35, blank=True)

    status = models.CharField(max_length=20, choices=REGISTRATION_STATUS, default='REGISTERED')
    attendance_status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='PENDING')
    registered_at = models.DateTimeField(auto_now_add=True)

    # Instant Digital Ticket & QR Code
    ticket_code = models.CharField(max_length=32, unique=True, blank=True, null=True, verbose_name="Unique Ticket Code")
    qr_code_image = models.ImageField(upload_to='events/qrcodes/', blank=True, null=True, verbose_name="Ticket QR Code")

    # Verifiable Certificate of Attendance
    certificate_id = models.CharField(max_length=32, unique=True, blank=True, null=True, verbose_name="Certificate ID")
    certificate_issued_at = models.DateTimeField(blank=True, null=True, verbose_name="Certificate Issue Date")

    class Meta:
        ordering = ['registered_at']
        unique_together = ('event', 'attendee_email')

    def __str__(self):
        return f"{self.attendee_name} -> {self.event.title} ({self.status}) [{self.ticket_code or 'NO-CODE'}]"

    def ensure_ticket_code(self):
        if not self.ticket_code:
            self.ticket_code = f"TC-EVT-{secrets.token_hex(4).upper()}"
        return self.ticket_code

    def generate_qr_code(self):
        self.ensure_ticket_code()
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        # Content encoded in the QR code: exact ticket identifier for scanner validation
        qr_data = self.ticket_code
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#111111", back_color="#FFFFFF")

        buffer = BytesIO()
        img.save(buffer)
        filename = f"qr_{self.ticket_code}.png"
        self.qr_code_image.save(filename, ContentFile(buffer.getvalue()), save=False)

    def issue_certificate_if_attended(self):
        if self.attendance_status == 'ATTENDED' and not self.certificate_id:
            self.certificate_id = f"TC-CERT-{secrets.token_hex(4).upper()}"
            self.certificate_issued_at = timezone.now()

    def save(self, *args, **kwargs):
        self.ensure_ticket_code()
        if self.attendance_status == 'ATTENDED' and not self.certificate_id:
            self.certificate_id = f"TC-CERT-{secrets.token_hex(4).upper()}"
            self.certificate_issued_at = timezone.now()

        if not self.qr_code_image:
            self.generate_qr_code()

        super().save(*args, **kwargs)

    @property
    def is_community_member(self):
        """Returns True if this ticket is associated with an active TechClub member profile."""
        return bool(self.member is not None)

    @property
    def attendee_type_label(self):
        return "Community Member" if self.is_community_member else "Public Guest"

    @property
    def pass_badge_title(self):
        if self.is_community_member:
            cohort_name = getattr(self.member, 'cohort', 'Member')
            return f"TechClub Member Pass • {cohort_name}"
        return "TechClub Public Guest Pass"

    @property
    def whatsapp_ticket_url(self):
        """Direct link to send confirmation and ticket pass to attendee's WhatsApp."""
        digits = ''.join(c for c in self.attendee_phone if c.isdigit())
        msg = (
            f"Assalamu Alaykum {self.attendee_name}!\n\n"
            f"Your registration for '{self.event.title}' is confirmed.\n"
            f"Ticket Code: {self.ticket_code}\n"
            f"Date: {self.event.start_datetime.strftime('%A, %b %d, %Y at %I:%M %p')}\n"
            f"Venue: {self.event.venue}\n\n"
            f"View your digital pass & QR code: http://127.0.0.1:8000/events/ticket/{self.ticket_code}/\n\n"
            f"TechClub Hargeisa — Connect. Learn. Build Together."
        )
        encoded = urllib.parse.quote(msg)
        return f"https://wa.me/{digits}?text={encoded}" if digits else f"https://api.whatsapp.com/send?text={encoded}"


import os

class EventResourceType(models.TextChoices):
    PDF = 'PDF', 'PDF Document'
    PRESENTATION = 'PRESENTATION', 'Slide Deck (PPT / Keynote)'
    SPREADSHEET = 'SPREADSHEET', 'Data / Spreadsheet (Excel / CSV)'
    DOCUMENT = 'DOCUMENT', 'Word / Document'
    ARCHIVE = 'ARCHIVE', 'Code / ZIP Archive'
    OTHER = 'OTHER', 'Reference Material'

class ResourceAccessRole(models.TextChoices):
    PUBLIC = 'PUBLIC', 'Everyone (Public & Guests)'
    MEMBER = 'MEMBER', 'TechClub Members Only'
    MENTOR = 'MENTOR', 'Mentors & Instructors Only'
    ORGANIZER = 'ORGANIZER', 'Organizers & Admins Only'

class EventResource(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200, verbose_name="Resource Title")
    file = models.FileField(upload_to='events/resources/', verbose_name="Resource File")
    resource_type = models.CharField(
        max_length=25,
        choices=EventResourceType.choices,
        default=EventResourceType.PDF,
        verbose_name="Resource Type"
    )
    access_role = models.CharField(
        max_length=20,
        choices=ResourceAccessRole.choices,
        default=ResourceAccessRole.PUBLIC,
        verbose_name="Target Access Role"
    )
    is_members_only = models.BooleanField(
        default=False,
        verbose_name="TechClub Members Only"
    )
    description = models.TextField(blank=True, verbose_name="Notes / Description")
    file_size_bytes = models.PositiveIntegerField(default=0, verbose_name="File Size (Bytes)")
    download_count = models.PositiveIntegerField(default=0, verbose_name="Download Count")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = "Event Resource"
        verbose_name_plural = "Event Resources"

    def __str__(self):
        return f"{self.title} ({self.get_resource_type_display()}) - {self.event.title}"

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, 'size') and not self.file_size_bytes:
            self.file_size_bytes = self.file.size
        # Auto-detect resource type from extension if left at default
        if self.file and self.resource_type == EventResourceType.PDF:
            ext = os.path.splitext(self.file.name)[1].lower()
            if ext in ('.ppt', '.pptx'):
                self.resource_type = EventResourceType.PRESENTATION
            elif ext in ('.xls', '.xlsx', '.csv'):
                self.resource_type = EventResourceType.SPREADSHEET
            elif ext in ('.doc', '.docx'):
                self.resource_type = EventResourceType.DOCUMENT
            elif ext in ('.zip', '.tar', '.gz'):
                self.resource_type = EventResourceType.ARCHIVE

        # Keep access_role and is_members_only synchronized
        if self.access_role != ResourceAccessRole.PUBLIC:
            self.is_members_only = True
        elif self.is_members_only:
            self.access_role = ResourceAccessRole.MEMBER

        super().save(*args, **kwargs)

    def increment_download_count(self):
        from django.db.models import F
        EventResource.objects.filter(id=self.id).update(download_count=F('download_count') + 1)
        self.refresh_from_db(fields=['download_count'])

    @property
    def is_public(self):
        return self.access_role == ResourceAccessRole.PUBLIC and not self.is_members_only

    @property
    def role_badge_info(self):
        if self.access_role == ResourceAccessRole.ORGANIZER:
            return {
                'label': 'Organizers Only',
                'short_label': 'Organizers',
                'icon': 'shield_person',
                'color': 'bg-rose-50 text-rose-800 border-rose-200',
            }
        elif self.access_role == ResourceAccessRole.MENTOR:
            return {
                'label': 'Mentors Only',
                'short_label': 'Mentors',
                'icon': 'stars',
                'color': 'bg-purple-50 text-purple-800 border-purple-200',
            }
        elif self.access_role == ResourceAccessRole.MEMBER or self.is_members_only:
            return {
                'label': 'Members Only',
                'short_label': 'Members',
                'icon': 'workspace_premium',
                'color': 'bg-amber-50 text-amber-800 border-amber-200',
            }
        return {
            'label': 'Public Access',
            'short_label': 'Public',
            'icon': 'public',
            'color': 'bg-emerald-50 text-emerald-800 border-emerald-200',
        }

    def can_user_download(self, user=None, is_community_member=False):
        """Determine if a given viewer can access/download this resource."""
        # Public resources are accessible to everyone
        if self.access_role == ResourceAccessRole.PUBLIC and not self.is_members_only:
            return True

        # Organizers/staff can access all materials
        if user and user.is_authenticated and (getattr(user, 'is_organizer', False) or user.is_staff or user.is_superuser):
            return True

        # Organizers-only resources
        if self.access_role == ResourceAccessRole.ORGANIZER:
            return bool(user and user.is_authenticated and (getattr(user, 'is_organizer', False) or user.is_staff or user.is_superuser))

        # Mentors-only resources
        if self.access_role == ResourceAccessRole.MENTOR:
            if not user or not user.is_authenticated:
                return False
            profile = getattr(user, 'profile', None)
            return bool(profile and getattr(profile, 'is_mentor', False))

        # Members-only resources
        if self.access_role == ResourceAccessRole.MEMBER or self.is_members_only:
            if is_community_member:
                return True
            if user and user.is_authenticated and hasattr(user, 'profile') and user.profile is not None:
                return True
            return False

        return True

    @property
    def formatted_file_size(self):
        bytes_val = self.file_size_bytes or 0
        if bytes_val >= 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.1f} MB"
        elif bytes_val >= 1024:
            return f"{bytes_val / 1024:.0f} KB"
        return f"{bytes_val} B"

    @property
    def file_extension(self):
        if self.file:
            return os.path.splitext(self.file.name)[1].lower()
        return ''

    @property
    def icon_name(self):
        mapping = {
            EventResourceType.PDF: 'picture_as_pdf',
            EventResourceType.PRESENTATION: 'slideshow',
            EventResourceType.SPREADSHEET: 'table_chart',
            EventResourceType.DOCUMENT: 'description',
            EventResourceType.ARCHIVE: 'folder_zip',
            EventResourceType.OTHER: 'attachment',
        }
        return mapping.get(self.resource_type, 'attachment')

    @property
    def badge_color_class(self):
        mapping = {
            EventResourceType.PDF: 'bg-red-100 text-red-800 border-red-200',
            EventResourceType.PRESENTATION: 'bg-orange-100 text-orange-800 border-orange-200',
            EventResourceType.SPREADSHEET: 'bg-emerald-100 text-emerald-800 border-emerald-200',
            EventResourceType.DOCUMENT: 'bg-blue-100 text-blue-800 border-blue-200',
            EventResourceType.ARCHIVE: 'bg-purple-100 text-purple-800 border-purple-200',
            EventResourceType.OTHER: 'bg-neutral-100 text-neutral-800 border-neutral-200',
        }
        return mapping.get(self.resource_type, 'bg-neutral-100 text-neutral-800 border-neutral-200')


class EventFeedback(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='feedbacks')
    registration = models.OneToOneField(EventRegistration, on_delete=models.CASCADE, related_name='feedback')
    rating = models.PositiveSmallIntegerField(
        choices=[(i, f"{i} Star{'s' if i > 1 else ''}") for i in range(1, 6)],
        default=5,
        verbose_name="Satisfaction Rating (1-5)"
    )
    feedback_text = models.TextField(blank=True, verbose_name="Attendee Feedback / Review")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Event Feedback"
        verbose_name_plural = "Event Feedbacks"

    def __str__(self):
        return f"{self.rating}★ by {self.registration.attendee_name} for {self.event.title}"



