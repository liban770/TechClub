from django.db import models
from django.conf import settings
from applications.models import ExperienceLevel, DisciplineCategory, Application

class Skill(models.Model):
    name = models.CharField(max_length=60, unique=True)
    category = models.CharField(max_length=60, blank=True, default="General")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class MemberProfile(models.Model):
    VISIBILITY_CHOICES = (
        ('PUBLIC', 'Public in Directory'),
        ('MEMBERS_ONLY', 'Community Members Only'),
        ('PRIVATE', 'Hidden / Private'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    application = models.OneToOneField(
        Application,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="member_profile"
    )

    full_name = models.CharField(max_length=150)
    professional_title = models.CharField(max_length=150, default="Software Builder")
    organization = models.CharField(max_length=150, blank=True, default="Independent")
    discipline = models.CharField(
        max_length=50,
        choices=DisciplineCategory.choices,
        default=DisciplineCategory.SOFTWARE_ENG
    )
    experience_level = models.CharField(
        max_length=40,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.JUNIOR
    )
    location = models.CharField(max_length=120, default="Hargeisa, Somaliland")
    bio = models.TextField(blank=True)
    
    avatar_url = models.CharField(max_length=500, blank=True)
    profile_photo = models.ImageField(upload_to='members/avatars/', blank=True, null=True, verbose_name="Profile Photo")
    is_mentor = models.BooleanField(default=False, verbose_name="Verified Active Mentor")
    cohort = models.CharField(max_length=50, default="Cohort #2")

    @property
    def display_avatar(self):
        if self.profile_photo:
            return self.profile_photo.url
        if self.avatar_url:
            return self.avatar_url
        return None

    # Links
    github_url = models.URLField(max_length=255, blank=True)
    linkedin_url = models.URLField(max_length=255, blank=True)
    portfolio_url = models.URLField(max_length=255, blank=True)

    # Privacy settings
    profile_visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='PUBLIC'
    )
    show_email = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=False)

    # Skills
    skills = models.ManyToManyField(Skill, blank=True, related_name="members")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.professional_title}"

    @property
    def initials(self):
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[1][0]}".upper()
        elif parts:
            return parts[0][:2].upper()
        return "TC"
