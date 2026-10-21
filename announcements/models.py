from django.db import models
from django.conf import settings

class AnnouncementCategory(models.TextChoices):
    EVENT = 'Upcoming Event', 'Upcoming Event'
    MENTORSHIP = 'Mentorship Opportunity', 'Mentorship Opportunity'
    WORKSHOP = 'Workshop & Lab', 'Workshop & Lab'
    CAREER = 'Career Opportunity', 'Career Opportunity'
    NEWS = 'Community News', 'Community News'
    NOTICE = 'Important Notice', 'Important Notice'

class AnnouncementAudience(models.TextChoices):
    ALL = 'ALL', 'All Visitors & Members'
    MEMBERS = 'MEMBERS', 'Approved Members Only'
    MENTORS = 'MENTORS', 'Active Mentors Only'
    ORGANIZERS = 'ORGANIZERS', 'Organizers Only'

class PublicationStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PUBLISHED = 'PUBLISHED', 'Published'
    ARCHIVED = 'ARCHIVED', 'Archived'

class Announcement(models.Model):
    title = models.CharField(max_length=200, verbose_name="Announcement Title")
    content = models.TextField(verbose_name="Content / Dispatch")
    category = models.CharField(
        max_length=40,
        choices=AnnouncementCategory.choices,
        default=AnnouncementCategory.NEWS
    )
    audience = models.CharField(
        max_length=20,
        choices=AnnouncementAudience.choices,
        default=AnnouncementAudience.ALL
    )
    publication_status = models.CharField(
        max_length=20,
        choices=PublicationStatus.choices,
        default=PublicationStatus.PUBLISHED
    )
    is_pinned = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"
