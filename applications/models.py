from django.db import models
from django.conf import settings
from django.utils import timezone

class ApplicationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Review'
    WAITLISTED = 'WAITLISTED', 'Waitlisted'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'

class ReferralSource(models.TextChoices):
    WHATSAPP = 'WhatsApp', 'WhatsApp Group / Chat'
    LINKEDIN = 'LinkedIn', 'LinkedIn'
    TIKTOK = 'TikTok', 'TikTok'
    INSTAGRAM = 'Instagram', 'Instagram'
    UNIVERSITY = 'University', 'University / Campus'
    TECH_CLUB = 'Tech Club', 'Tech Club / Meetup'
    FRIEND = 'Friend', 'Colleague / Friend Referral'
    COMMUNITY_EVENT = 'Community Event', 'Community Event / Conference'
    OTHER = 'Other', 'Other'

class ExperienceLevel(models.TextChoices):
    JUNIOR = 'Junior (1-2y)', 'Junior (1-2y)'
    MID = 'Mid-level (3-5y)', 'Mid-level (3-5y)'
    SENIOR = 'Senior (5-8y)', 'Senior (5-8y)'
    LEAD = 'Staff & Lead (8y+)', 'Staff & Lead (8y+)'

class DisciplineCategory(models.TextChoices):
    SOFTWARE_ENG = 'Software Engineering', 'Software Engineering'
    DESIGN = 'Product & UI/UX', 'Product & UI/UX'
    DEVOPS = 'Cloud & DevOps', 'Cloud & DevOps'
    AI_DATA = 'Data & AI', 'Data & AI'
    FOUNDERS = 'Tech Founders', 'Tech Founders'
    CYBERSECURITY = 'Cybersecurity', 'Cybersecurity'
    OTHER = 'Other', 'Other Technical Field'

class Application(models.Model):
    # Personal Info
    full_name = models.CharField(max_length=150, verbose_name="Full Name")
    email = models.EmailField(verbose_name="Email Address")
    phone = models.CharField(max_length=35, verbose_name="Phone Number")
    city = models.CharField(max_length=100, default="Hargeisa", verbose_name="City")

    # Professional Info
    current_role = models.CharField(max_length=150, verbose_name="Current Role / Title")
    professional_category = models.CharField(
        max_length=50,
        choices=DisciplineCategory.choices,
        default=DisciplineCategory.SOFTWARE_ENG,
        verbose_name="Discipline / Category"
    )
    organization = models.CharField(max_length=150, blank=True, verbose_name="Organization / University")
    experience_level = models.CharField(
        max_length=40,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.JUNIOR,
        verbose_name="Experience Level"
    )
    skills = models.CharField(max_length=300, blank=True, verbose_name="Key Skills (comma-separated)")
    profile_summary = models.TextField(verbose_name="Profile Summary / Bio")

    # Goals & Interests
    interests = models.CharField(max_length=300, blank=True, verbose_name="Networking Goals")
    referral_source = models.CharField(
        max_length=50,
        choices=ReferralSource.choices,
        default=ReferralSource.WHATSAPP,
        verbose_name="Referral Source"
    )

    # Links
    github_url = models.URLField(max_length=255, blank=True, verbose_name="GitHub Profile")
    linkedin_url = models.URLField(max_length=255, blank=True, verbose_name="LinkedIn Profile")
    portfolio_url = models.URLField(max_length=255, blank=True, verbose_name="Portfolio or Website")

    # Review Workflow
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
        verbose_name="Application Status"
    )
    organizer_notes = models.TextField(blank=True, verbose_name="Internal Review Notes")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_applications",
        verbose_name="Reviewed By"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Reviewed At")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Membership Application"
        verbose_name_plural = "Membership Applications"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.get_status_display()})"

    def mark_reviewed(self, new_status, organizer_user, notes=None):
        self.status = new_status
        self.reviewed_by = organizer_user
        self.reviewed_at = timezone.now()
        if notes:
            self.organizer_notes = notes
        self.save()

class NotificationLog(models.Model):
    NOTIFICATION_TYPES = (
        ('APPLICATION_RECEIVED', 'Application Received Confirmation'),
        ('APPLICATION_APPROVED', 'Application Approved & Password Link'),
        ('APPLICATION_WAITLISTED', 'Application Waitlisted Notice'),
        ('APPLICATION_REJECTED', 'Application Rejected Notice'),
        ('EVENT_REGISTRATION', 'Event Registration Confirmation'),
        ('PASSWORD_RESET_OTP', 'Password Reset OTP Verification Code'),
        ('ORGANIZER_NOTICE', 'Organizer Administrative Notice'),
    )

    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=150, blank=True)
    message_type = models.CharField(max_length=40, choices=NOTIFICATION_TYPES)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    activation_url = models.CharField(max_length=500, blank=True, null=True)
    delivery_status = models.CharField(max_length=150, default="Delivered (Local / In-App)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.message_type} to {self.recipient_email} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"
