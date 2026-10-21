from django.db import models
from django.conf import settings
from members.models import MemberProfile

class MeetingPurpose(models.TextChoices):
    MENTORSHIP = '1-on-1 Mentorship', '1-on-1 Mentorship'
    REVIEW = 'Architecture Review', 'Architecture Review'
    CAREER = 'Career Guidance', 'Career Guidance'
    COLLABORATION = 'Project Collaboration', 'Project Collaboration'
    SYNC = 'Community Planning & Sync', 'Community Planning & Sync'

class MeetingStatus(models.TextChoices):
    SCHEDULED = 'SCHEDULED', 'Scheduled'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    RESCHEDULED = 'RESCHEDULED', 'Rescheduled'

class Meeting(models.Model):
    title = models.CharField(max_length=200, verbose_name="Meeting Title")
    purpose = models.CharField(
        max_length=60,
        choices=MeetingPurpose.choices,
        default=MeetingPurpose.MENTORSHIP
    )
    start_datetime = models.DateTimeField(verbose_name="Start Date & Time")
    end_datetime = models.DateTimeField(verbose_name="End Date & Time")
    venue = models.CharField(max_length=200, default="Hargeisa, Somaliland")
    meeting_link = models.URLField(max_length=255, blank=True)
    cover_image = models.ImageField(upload_to='meetings/covers/', blank=True, null=True, verbose_name="Meeting Cover / Banner")
    status = models.CharField(
        max_length=20,
        choices=MeetingStatus.choices,
        default=MeetingStatus.SCHEDULED
    )
    organizer_notes = models.TextField(blank=True, verbose_name="Internal Organizer Notes")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_datetime']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def display_cover_image(self):
        if self.cover_image:
            return self.cover_image.url
        return "/static/images/speaker-hero.png"

class MeetingParticipant(models.Model):
    ROLE_CHOICES = (
        ('MENTOR', 'Senior Mentor'),
        ('MENTEE', 'Mentee / Learner'),
        ('COLLABORATOR', 'Collaborator'),
        ('ORGANIZER', 'Community Organizer'),
    )
    PARTICIPATION_STATUS = (
        ('INVITED', 'Invited'),
        ('ACCEPTED', 'Accepted'),
        ('DECLINED', 'Declined'),
    )

    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='participants')
    member = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name='meeting_participations')
    role_in_meeting = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MENTEE')
    status = models.CharField(max_length=20, choices=PARTICIPATION_STATUS, default='ACCEPTED')

    class Meta:
        unique_together = ('meeting', 'member')

    def __str__(self):
        return f"{self.member.full_name} ({self.get_role_in_meeting_display()}) in {self.meeting.title}"
