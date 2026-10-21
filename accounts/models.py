from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import secrets
from datetime import timedelta

class UserRole(models.TextChoices):
    ORGANIZER = 'ORGANIZER', 'Organizer / Admin'
    MEMBER = 'MEMBER', 'Community Member'
    APPLICANT = 'APPLICANT', 'Applicant'

class User(AbstractUser):
    email = models.EmailField(unique=True, verbose_name="Email Address")
    phone = models.CharField(max_length=35, blank=True, null=True, verbose_name="Phone Number")
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.APPLICANT,
        verbose_name="User Role"
    )
    activation_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
    activation_token_created_at = models.DateTimeField(null=True, blank=True, verbose_name="Token Created At")
    must_set_password = models.BooleanField(default=False)

    # Password Recovery via Email OTP
    otp_code = models.CharField(max_length=6, blank=True, null=True, verbose_name="OTP Code")
    otp_created_at = models.DateTimeField(null=True, blank=True, verbose_name="OTP Created At")
    otp_failed_attempts = models.IntegerField(default=0, verbose_name="OTP Failed Attempts")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['-date_joined']

    def __str__(self):
        full = self.get_full_name()
        return f"{full} ({self.email})" if full else self.email

    @property
    def is_organizer(self):
        return self.role == UserRole.ORGANIZER or self.is_superuser or self.is_staff

    @property
    def is_community_member(self):
        return self.role == UserRole.MEMBER

    def generate_activation_token(self):
        self.activation_token = secrets.token_urlsafe(32)
        self.activation_token_created_at = timezone.now()
        self.must_set_password = True
        self.save(update_fields=['activation_token', 'activation_token_created_at', 'must_set_password'])
        return self.activation_token

    def is_activation_token_valid(self):
        """Enforces a 72-hour maximum lifetime for member setup tokens."""
        if not self.activation_token:
            return False
        if self.activation_token_created_at:
            return timezone.now() - self.activation_token_created_at <= timedelta(hours=72)
        return True

    def generate_otp(self):
        """Generates a secure 6-digit numeric OTP code valid for 15 minutes and resets failed attempts."""
        code = f"{secrets.randbelow(900000) + 100000}"
        self.otp_code = code
        self.otp_created_at = timezone.now()
        self.otp_failed_attempts = 0
        self.save(update_fields=['otp_code', 'otp_created_at', 'otp_failed_attempts'])
        return code

    def verify_otp(self, code):
        """Validates OTP code, enforces a 5-attempt brute-force ceiling, and checks 15-minute expiration."""
        if not self.otp_code or not code:
            return False
        if not self.otp_created_at or (timezone.now() - self.otp_created_at > timedelta(minutes=15)):
            self.clear_otp()
            return False
        if self.otp_failed_attempts >= 5:
            # Auto-burn OTP after 5 consecutive failed attempts to defeat brute-force
            self.clear_otp()
            return False

        if str(self.otp_code).strip() != str(code).strip():
            self.otp_failed_attempts += 1
            if self.otp_failed_attempts >= 5:
                self.clear_otp()
            else:
                self.save(update_fields=['otp_failed_attempts'])
            return False

        return True

    def clear_otp(self):
        self.otp_code = None
        self.otp_created_at = None
        self.otp_failed_attempts = 0
        self.save(update_fields=['otp_code', 'otp_created_at', 'otp_failed_attempts'])


class InAppNotification(models.Model):
    NOTIFICATION_TYPES = (
        ('INFO', 'Information'),
        ('SUCCESS', 'Success Notification'),
        ('WARNING', 'Warning / Action Required'),
        ('APPLICATION', 'Application Status'),
        ('EVENT', 'Event / RSVP Update'),
        ('MEETING', 'Mentorship / Meeting Notice'),
        ('SECURITY', 'Account & Security'),
    )

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='INFO')
    link = models.CharField(max_length=300, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "In-App Notification"
        verbose_name_plural = "In-App Notifications"

    def __str__(self):
        return f"{self.title} to {self.recipient.email} ({'Read' if self.is_read else 'Unread'})"


class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    activity_type = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "User Activity"
        verbose_name_plural = "User Activities"

    def __str__(self):
        user_str = self.user.email if self.user else "Anonymous / System"
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {user_str}: {self.title}"


def log_activity(user, activity_type, title, description="", request=None):
    ip = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
    return UserActivity.objects.create(
        user=user if getattr(user, 'is_authenticated', False) or isinstance(user, User) else None,
        activity_type=activity_type,
        title=title,
        description=description,
        ip_address=ip
    )


def notify_user(user, title, message, notification_type="INFO", link=None):
    if user and (getattr(user, 'is_authenticated', False) or isinstance(user, User)):
        return InAppNotification.objects.create(
            recipient=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link
        )
    return None

