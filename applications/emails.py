from django.core.mail import send_mail
from django.conf import settings
from .models import NotificationLog

def send_application_confirmation(application, request=None):
    subject = "TechClub — We received your membership application"
    content = f"""Dear {application.full_name},

Thank you for applying to TechClub Hargeisa.

We have received your application for the {application.current_role} track. 
Our community organizers review each submission within 48 hours to ensure a high-trust, collaborative ecosystem.

Your Application Summary:
- Name: {application.full_name}
- Email: {application.email}
- Discipline: {application.professional_category}
- Experience: {application.experience_level}
- Referral Source: {application.referral_source}

You will receive an update once our organizers have completed the review.

Warm regards,
TechClub Admissions Team
Hargeisa, Somaliland
"""
    status_str = "Delivered (Logged)"
    try:
        send_mail(
            subject=subject,
            message=content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            fail_silently=True
        )
    except Exception as e:
        status_str = f"Queued (Simulated: {str(e)[:40]})"

    try:
        NotificationLog.objects.create(
            recipient_email=application.email,
            recipient_name=application.full_name,
            message_type='APPLICATION_RECEIVED',
            subject=subject,
            content=content,
            delivery_status=status_str[:120]
        )
    except Exception:
        pass

def send_approval_notification(application, user, request=None):
    token = user.activation_token
    if request:
        base_url = request.build_absolute_uri('/')[:-1]
    else:
        base_url = "http://127.0.0.1:8000"
    activation_url = f"{base_url}/accounts/activate/{token}/"

    subject = "Welcome to TechClub! Set up your member account"
    content = f"""Congratulations {application.full_name}!

Your application to TechClub Hargeisa has been officially APPROVED.
You are now part of our vetted network of engineers, founders, and creators.

Please use the secure link below to set your password and access your member profile:
{activation_url}

From your member dashboard, you will be able to:
1. Complete your public and private member profile
2. Connect with experienced mentors and peers in the directory
3. Register for exclusive community meetups and architecture labs
4. Schedule 1-on-1 mentorship sessions

Welcome aboard!
TechClub Organizing Board
Hargeisa Node
"""
    status_str = "Delivered (Logged)"
    try:
        send_mail(
            subject=subject,
            message=content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            fail_silently=True
        )
    except Exception as e:
        status_str = f"Queued (Simulated: {str(e)[:40]})"

    try:
        NotificationLog.objects.create(
            recipient_email=application.email,
            recipient_name=application.full_name,
            message_type='APPLICATION_APPROVED',
            subject=subject,
            content=content,
            activation_url=activation_url,
            delivery_status=status_str[:120]
        )
    except Exception:
        pass

def send_status_update_notification(application, status_type, notes=None):
    if status_type == 'WAITLISTED':
        subject = "TechClub — Update on your membership application"
        content = f"""Dear {application.full_name},

Thank you for your application to TechClub Hargeisa.
Due to high cohort volume, your profile has been placed on our Priority Waiting List for the upcoming admissions batch.

{f'Organizer note: {notes}' if notes else ''}

We periodically admit waitlisted candidates as capacity expands. We will notify you immediately once a seat opens.

Warm regards,
TechClub Admissions Team
"""
        msg_type = 'APPLICATION_WAITLISTED'
    else:
        subject = "TechClub — Application review status"
        content = f"""Dear {application.full_name},

Thank you for your interest in TechClub Hargeisa.
After reviewing your application, our team has decided not to proceed with membership at this time.

{f'Organizer feedback: {notes}' if notes else ''}

We appreciate your commitment to your technology journey and encourage you to re-apply in future cohorts.

Best wishes,
TechClub Admissions Team
"""
        msg_type = 'APPLICATION_REJECTED'

    status_str = "Delivered (Logged)"
    try:
        send_mail(
            subject=subject,
            message=content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            fail_silently=True
        )
    except Exception as e:
        status_str = f"Queued (Simulated: {str(e)[:40]})"

    try:
        NotificationLog.objects.create(
            recipient_email=application.email,
            recipient_name=application.full_name,
            message_type=msg_type,
            subject=subject,
            content=content,
            delivery_status=status_str[:120]
        )
    except Exception:
        pass

def send_event_registration_confirmation(registration, request=None):
    subject = f"Confirmed: RSVP for {registration.event.title}"
    content = f"""Dear {registration.attendee_name},

Your registration for '{registration.event.title}' is CONFIRMED!

Event Details:
- Title: {registration.event.title}
- Date & Time: {registration.event.start_datetime.strftime('%A, %b %d, %Y at %I:%M %p')}
- Venue: {registration.event.venue}
- Status: {registration.get_status_display()}

Please arrive 15 minutes before start time for check-in.

See you there!
TechClub Events Team
"""
    status_str = "Delivered (Logged)"
    try:
        send_mail(
            subject=subject,
            message=content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[registration.attendee_email],
            fail_silently=True
        )
    except Exception as e:
        status_str = f"Queued (Simulated: {str(e)[:40]})"

    try:
        NotificationLog.objects.create(
            recipient_email=registration.attendee_email,
            recipient_name=registration.attendee_name,
            message_type='EVENT_REGISTRATION',
            subject=subject,
            content=content,
            delivery_status=status_str[:120]
        )
    except Exception:
        pass

def send_password_reset_otp(user, otp_code, request=None):
    recipient_name = user.get_full_name() or user.username
    subject = "TechClub — Your Password Reset Verification Code"
    content = f"""Dear {recipient_name},

You requested to reset your password for your TechClub account ({user.email}).

Your 6-digit verification code (OTP) is:
****************
   {otp_code}
****************

This verification code will expire in 15 minutes.

If you did not request this password reset, please ignore this email or notify the TechClub organizers immediately.

Warm regards,
TechClub Security Operations
Hargeisa, Somaliland
"""
    status_str = "Delivered (Logged)"
    try:
        send_mail(
            subject=subject,
            message=content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True
        )
    except Exception as e:
        status_str = f"Queued (Simulated: {str(e)[:40]})"

    try:
        NotificationLog.objects.create(
            recipient_email=user.email,
            recipient_name=recipient_name,
            message_type='PASSWORD_RESET_OTP',
            subject=subject,
            content=content,
            delivery_status=status_str[:120]
        )
    except Exception:
        pass

