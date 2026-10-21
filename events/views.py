import os
import csv
import base64
import io
import qrcode
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.utils import timezone
from .models import (
    Event, EventRegistration, EventCategory, EventStatus, EventMode, EventAudienceRole,
    EventResource, EventResourceType, ResourceAccessRole, EventFeedback
)
from members.models import MemberProfile
from applications.emails import send_event_registration_confirmation
from django.core.exceptions import ValidationError
from techclub_core.validators import validate_uploaded_image, validate_uploaded_document
from accounts.models import log_activity, notify_user

def is_organizer(user):
    return user.is_authenticated and user.is_organizer

# --- PUBLIC EVENT VIEWS ---

def public_events_view(request):
    role_filter = request.GET.get('role', 'ALL').strip().upper()
    mode_filter = request.GET.get('mode', 'ALL').strip().upper()

    events = Event.objects.filter(status__in=[EventStatus.OPEN, EventStatus.FULL])
    if role_filter in ['PUBLIC', 'MEMBER', 'MENTOR']:
        events = events.filter(audience_role=role_filter)
    if mode_filter in ['IN_PERSON', 'ONLINE', 'HYBRID']:
        events = events.filter(event_mode=mode_filter)

    events = events.order_by('start_datetime')
    completed_events = Event.objects.filter(status=EventStatus.COMPLETED).order_by('-start_datetime')[:3]
    return render(request, 'events/public_events.html', {
        'events': events,
        'completed_events': completed_events,
        'role_filter': role_filter,
        'mode_filter': mode_filter,
        'audience_roles': EventAudienceRole.choices,
    })

from django.db import IntegrityError
from accounts.models import User

def event_detail_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    user_registered = False
    reg_status = None
    registration = None

    if request.user.is_authenticated:
        reg = EventRegistration.objects.filter(event=event, attendee_email__iexact=request.user.email).first()
        if not reg and hasattr(request.user, 'profile'):
            reg = EventRegistration.objects.filter(event=event, member=request.user.profile).first()
        if reg:
            user_registered = True
            reg_status = reg.status
            registration = reg

    user_is_member = False
    if registration and registration.is_community_member:
        user_is_member = True
    elif request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile is not None:
        user_is_member = True

    resources = event.resources.all()
    # Annotate access permissions on each resource
    for res in resources:
        res.user_can_access = res.can_user_download(user=request.user, is_community_member=user_is_member)

    return render(request, 'events/event_detail.html', {
        'event': event,
        'user_registered': user_registered,
        'reg_status': reg_status,
        'registration': registration,
        'resources': resources,
        'is_community_member': user_is_member,
        'resource_roles': ResourceAccessRole.choices,
    })

def event_register_action(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':
        # 1. Check event lifecycle status and completion
        if event.status in [EventStatus.DRAFT, EventStatus.CANCELLED, EventStatus.COMPLETED] or event.is_past:
            messages.error(request, "This event is closed or no longer accepting registrations.")
            return redirect('event_detail', event_id=event.id)

        # 2. Check registration deadline
        if event.registration_deadline and timezone.now() > event.registration_deadline:
            messages.error(request, "Registration for this event has closed (deadline has passed).")
            return redirect('event_detail', event_id=event.id)

        # 3. Enforce Audience Role Access Control
        if event.audience_role == EventAudienceRole.MEMBER:
            user_has_member_access = request.user.is_authenticated and (hasattr(request.user, 'profile') or request.user.is_organizer)
            if not user_has_member_access:
                messages.error(request, "This event is exclusive to verified TechClub members. Please sign in with your verified account or apply for membership.")
                return redirect('event_detail', event_id=event.id)

        elif event.audience_role == EventAudienceRole.MENTOR:
            user_has_mentor_access = request.user.is_authenticated and (getattr(getattr(request.user, 'profile', None), 'is_mentor', False) or request.user.is_organizer)
            if not user_has_mentor_access:
                messages.error(request, "This session is exclusive to TechClub instructors and verified mentors.")
                return redirect('event_detail', event_id=event.id)

        # 4. Check if logged-in user account is deactivated
        if request.user.is_authenticated and not request.user.is_active:
            messages.error(request, "Your TechClub account is deactivated. You cannot register for events. Please contact organizers.")
            return redirect('event_detail', event_id=event.id)

        if request.user.is_authenticated:
            name = request.user.get_full_name() or request.user.username
            email = request.user.email.strip().lower()
            phone = getattr(request.user, 'phone', '') or ''
            member_profile = getattr(request.user, 'profile', None)
        else:
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip().lower()
            phone = request.POST.get('phone', '').strip()
            member_profile = None

        if not name or not email:
            messages.error(request, "Name and Email are required to register.")
            return redirect('event_detail', event_id=event.id)

        # 5. Check if this email belongs to a deactivated member account
        matched_user = User.objects.filter(email__iexact=email).first()
        if matched_user and not matched_user.is_active:
            messages.error(request, "The account associated with this email address has been deactivated. Please contact TechClub organizers.")
            return redirect('event_detail', event_id=event.id)

        # 3. Check duplicate registration by email or member profile
        existing = EventRegistration.objects.filter(event=event, attendee_email__iexact=email).first()
        if not existing and member_profile:
            existing = EventRegistration.objects.filter(event=event, member=member_profile).first()

        if existing:
            messages.warning(
                request, 
                f"You are already registered for this event! Here is your official Digital Ticket Pass (Ticket ID: {existing.ticket_code})."
            )
            return redirect('event_ticket', ticket_code=existing.ticket_code)

        # 4. Capacity and Waiting list logic
        if event.is_full:
            reg_status = 'WAITLISTED'
            flash_msg = f"Event has reached maximum capacity ({event.capacity} seats). You have been added to the Priority Waiting List!"
        else:
            reg_status = 'REGISTERED'
            flash_msg = f"Your RSVP for '{event.title}' is confirmed! Your digital ticket with QR code has been generated."

        try:
            registration = EventRegistration.objects.create(
                event=event,
                member=member_profile,
                attendee_name=name,
                attendee_email=email,
                attendee_phone=phone,
                status=reg_status,
                attendance_status='PENDING'
            )
        except IntegrityError:
            existing = EventRegistration.objects.filter(event=event, attendee_email__iexact=email).first()
            if existing:
                messages.info(request, f"You are already registered! Here is your digital pass: {existing.ticket_code}")
                return redirect('event_ticket', ticket_code=existing.ticket_code)
            messages.error(request, "A registration conflict occurred. Please refresh the page.")
            return redirect('event_detail', event_id=event.id)

        # Update event status if capacity reached
        if event.is_full and event.status == EventStatus.OPEN:
            event.status = EventStatus.FULL
            event.save()

        # Send confirmation email
        try:
            send_event_registration_confirmation(registration, request)
        except Exception:
            pass

        log_activity(
            request.user if request.user.is_authenticated else None,
            'EVENT_RSVP',
            f"Event RSVP: {event.title}",
            f"{name} registered for '{event.title}' ({reg_status}). Ticket: {registration.ticket_code}.",
            request=request
        )

        if request.user.is_authenticated:
            notify_user(
                request.user,
                f"RSVP Confirmed: {event.title}",
                f"Your registration for {event.title} is confirmed ({reg_status}). Ticket: {registration.ticket_code}.",
                "EVENT",
                link=f"/events/ticket/{registration.ticket_code}/"
            )

        messages.success(request, flash_msg)
        return redirect('event_ticket', ticket_code=registration.ticket_code)

    return redirect('event_detail', event_id=event.id)

def event_ticket_view(request, ticket_code):
    registration = get_object_or_404(EventRegistration, ticket_code__iexact=ticket_code.strip())
    event = registration.event
    resources = event.resources.all()
    user_is_member = registration.is_community_member or bool(request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile is not None)

    for res in resources:
        res.user_can_access = res.can_user_download(user=request.user, is_community_member=user_is_member)

    user_feedback = getattr(registration, 'feedback', None)
    if not user_feedback:
        user_feedback = EventFeedback.objects.filter(registration=registration).first()

    return render(request, 'events/digital_ticket.html', {
        'registration': registration,
        'event': event,
        'resources': resources,
        'is_community_member': user_is_member,
        'resource_roles': ResourceAccessRole.choices,
        'user_feedback': user_feedback,
    })

def event_join_live_view(request, ticket_code):
    """
    Automatic Verified Join:
    When an attendee clicks 'Join Live Class', this view:
    1. Validates their ticket and event status.
    2. Automatically marks attendance as 'ATTENDED' and issues official certificate.
    3. Sends in-app notification with the certificate link.
    4. Seamlessly forwards the attendee to the online Zoom/Meet meeting URL.
    """
    registration = get_object_or_404(EventRegistration, ticket_code__iexact=ticket_code.strip())
    event = registration.event

    if not event.meeting_url:
        messages.warning(request, f"Online meeting link for '{event.title}' is not active yet. Please contact event organizers.")
        return redirect('event_ticket', ticket_code=registration.ticket_code)

    was_attended = (registration.attendance_status == 'ATTENDED')
    if not was_attended:
        registration.attendance_status = 'ATTENDED'
        registration.issue_certificate_if_attended()
        registration.save()

        # Send in-app notification with official certificate link
        if registration.member and registration.member.user:
            notify_user(
                registration.member.user,
                f"🎓 Live Attendance Verified: {event.title}",
                f"Your online attendance for '{event.title}' has been confirmed and your official certificate has been issued! Certificate ID: {registration.certificate_id}.",
                "CERTIFICATE",
                link=f"/events/certificate/{registration.certificate_id}/"
            )

        log_activity(
            request.user if request.user.is_authenticated else None,
            'LIVE_CLASS_JOIN',
            f"Live Session Joined: {event.title}",
            f"Attendee {registration.attendee_name} joined online class for '{event.title}'. Certificate {registration.certificate_id} issued.",
            request=request
        )

    return redirect(event.meeting_url)

def event_certificate_view(request, certificate_id):
    registration = get_object_or_404(EventRegistration, certificate_id__iexact=certificate_id.strip())
    if registration.attendance_status != 'ATTENDED':
        messages.error(request, "Certificates are only unlocked once attendance is officially verified by an organizer.")
        return redirect('event_ticket', ticket_code=registration.ticket_code)

    # Full canonical verification URL
    verification_url = request.build_absolute_uri(reverse('verify_certificate', args=[registration.certificate_id]))

    # Clean display URL formatted like Coursera/edX (e.g. techclub.so/verify/TC-CERT-...)
    clean_host = request.get_host()
    clean_verify_url = f"{clean_host}/verify/{registration.certificate_id}"

    # Generate dedicated certificate verification QR Code (points to live URL)
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=1
        )
        qr.add_data(verification_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#111111", back_color="#FFFFFF")
        buf = io.BytesIO()
        img.save(buf)
        certificate_qr_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception:
        certificate_qr_b64 = None

    return render(request, 'events/certificate.html', {
        'registration': registration,
        'event': registration.event,
        'verification_url': verification_url,
        'clean_verify_url': clean_verify_url,
        'certificate_qr_b64': certificate_qr_b64,
    })

def event_certificate_pdf_view(request, certificate_id):
    """
    Generates and downloads an official high-resolution, vector-rendered
    PDF certificate of completion with embedded verification QR code and styling.
    """
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import ImageReader

    registration = get_object_or_404(EventRegistration, certificate_id__iexact=certificate_id.strip())
    if registration.attendance_status != 'ATTENDED':
        messages.error(request, "Certificates are only available once attendance is officially verified.")
        return redirect('event_ticket', ticket_code=registration.ticket_code)

    verification_url = request.build_absolute_uri(reverse('verify_certificate', args=[registration.certificate_id]))

    # Generate QR Code image for the PDF
    qr = qrcode.QRCode(version=1, box_size=8, border=1)
    qr.add_data(verification_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer)
    qr_buffer.seek(0)
    qr_reader = ImageReader(qr_buffer)

    # 11 x 8.5 inches landscape (792 x 612 pt)
    pdf_buffer = io.BytesIO()
    p = canvas.Canvas(pdf_buffer, pagesize=landscape(letter))
    page_w, page_h = landscape(letter)

    # Colors
    navy = HexColor('#0F172A')
    gold = HexColor('#D97706')
    dark_gold = HexColor('#92400E')
    soft_bg = HexColor('#FAFAF9')
    slate = HexColor('#475569')

    # Background
    p.setFillColor(soft_bg)
    p.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    # Outer Double Border (Navy + Gold)
    p.setStrokeColor(navy)
    p.setLineWidth(5)
    p.rect(24, 24, page_w - 48, page_h - 48, fill=0, stroke=1)

    p.setStrokeColor(gold)
    p.setLineWidth(1.5)
    p.rect(32, 32, page_w - 64, page_h - 64, fill=0, stroke=1)

    # Corner Decorative Accents
    corner_size = 20
    p.setStrokeColor(dark_gold)
    p.setLineWidth(2)
    p.line(40, page_h - 40, 40 + corner_size, page_h - 40)
    p.line(40, page_h - 40, 40, page_h - 40 - corner_size)
    p.line(page_w - 40, page_h - 40, page_w - 40 - corner_size, page_h - 40)
    p.line(page_w - 40, page_h - 40, page_w - 40, page_h - 40 - corner_size)
    p.line(40, 40, 40 + corner_size, 40)
    p.line(40, 40, 40, 40 + corner_size)
    p.line(page_w - 40, 40, page_w - 40 - corner_size, 40)
    p.line(page_w - 40, 40, page_w - 40, 40 + corner_size)

    # Header Ribbon & Organization Brand
    p.setFillColor(dark_gold)
    p.setFont('Helvetica-Bold', 11)
    p.drawCentredString(page_w / 2, page_h - 75, "TECHCLUB HARGEISA - SOMALILAND INNOVATION HUB")

    p.setFillColor(navy)
    p.setFont('Helvetica-Bold', 26)
    p.drawCentredString(page_w / 2, page_h - 110, "CERTIFICATE OF ATTENDANCE")

    p.setFillColor(slate)
    p.setFont('Helvetica', 11)
    p.drawCentredString(page_w / 2, page_h - 135, "THIS OFFICIAL CREDENTIAL IS PROUDLY CONFERRED UPON")

    # Recipient Name (Prominent & Stylized with dynamic scaling)
    p.setFillColor(navy)
    attendee_name = registration.attendee_name
    name_font_size = 28 if len(attendee_name) < 28 else (22 if len(attendee_name) < 42 else 18)
    p.setFont('Helvetica-Bold', name_font_size)
    p.drawCentredString(page_w / 2, page_h - 185, attendee_name)

    # Elegant divider under name
    p.setStrokeColor(gold)
    p.setLineWidth(1)
    p.line(page_w / 2 - 180, page_h - 198, page_w / 2 + 180, page_h - 198)

    # Achievement Description
    p.setFillColor(slate)
    p.setFont('Helvetica', 11)
    p.drawCentredString(page_w / 2, page_h - 230, "for verified active attendance and completion of the technical masterclass:")

    # Masterclass Title
    p.setFillColor(navy)
    p.setFont('Helvetica-Bold', 19)
    title_display = registration.event.title
    if len(title_display) > 65:
        title_display = title_display[:62] + '...'
    p.drawCentredString(page_w / 2, page_h - 265, title_display)

    # Event Metadata (Category, Date)
    p.setFillColor(slate)
    p.setFont('Helvetica', 10)
    event_date_str = registration.event.start_datetime.strftime('%B %d, %Y')
    venue_str = "Online Live Session" if registration.event.event_mode == 'ONLINE' else registration.event.venue
    p.drawCentredString(page_w / 2, page_h - 290, f"Conducted on {event_date_str} • Category: {registration.event.category} • {venue_str}")

    # Bottom Verification & Signature Area
    # Left: Official Signature / Issuer Authority
    p.setStrokeColor(slate)
    p.setLineWidth(0.8)
    p.line(80, 115, 260, 115)

    p.setFillColor(navy)
    p.setFont('Helvetica-Bold', 11)
    p.drawCentredString(170, 100, "Mustafe Said Duale")
    p.setFillColor(slate)
    p.setFont('Helvetica', 9)
    p.drawCentredString(170, 87, "Founder & Director, TechClub")
    p.drawCentredString(170, 75, f"Issued: {registration.certificate_issued_at.strftime('%B %d, %Y') if registration.certificate_issued_at else event_date_str}")

    # Center: High-Resolution Verification QR Code
    qr_x = (page_w / 2) - 40
    qr_y = 65
    p.drawImage(qr_reader, qr_x, qr_y, width=80, height=80)
    p.setFillColor(slate)
    p.setFont('Helvetica-Bold', 7)
    p.drawCentredString(page_w / 2, 53, "SCAN TO VERIFY CREDENTIAL")

    # Right: Verification ID & Security Seal
    p.setStrokeColor(slate)
    p.setLineWidth(0.8)
    p.line(page_w - 260, 115, page_w - 80, 115)

    p.setFillColor(navy)
    p.setFont('Helvetica-Bold', 11)
    p.drawCentredString(page_w - 170, 100, "Official Credential ID")
    p.setFillColor(dark_gold)
    p.setFont('Courier-Bold', 10)
    p.drawCentredString(page_w - 170, 87, registration.certificate_id)
    p.setFillColor(slate)
    p.setFont('Helvetica', 8)
    clean_host = request.get_host()
    p.drawCentredString(page_w - 170, 75, f"{clean_host}/verify/{registration.certificate_id}")

    # Finalize PDF
    p.showPage()
    p.save()

    pdf_bytes = pdf_buffer.getvalue()
    filename = f"TechClub_Certificate_{registration.certificate_id}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
@user_passes_test(is_organizer)
def admin_ticket_scan_view(request):
    if request.method == 'POST':
        ticket_code = request.POST.get('ticket_code', '').strip().upper()
        if not ticket_code:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Ticket code is required.'}, status=400)
            messages.error(request, "Please enter or scan a ticket code.")
            return redirect('admin_ticket_scan')

        registration = EventRegistration.objects.filter(ticket_code__iexact=ticket_code).first()
        if not registration:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': f"Ticket Code '{ticket_code}' not recognized."}, status=404)
            messages.error(request, f"Ticket Code '{ticket_code}' was not found in our registry.")
            return redirect('admin_ticket_scan')

        already_attended = (registration.attendance_status == 'ATTENDED')
        registration.attendance_status = 'ATTENDED'
        registration.issue_certificate_if_attended()
        registration.save()

        if not already_attended and registration.member and registration.member.user:
            notify_user(
                registration.member.user,
                f"🎓 Certificate Issued: {registration.event.title}",
                f"Your ticket check-in is complete! Your official certificate has been verified and issued. Certificate ID: {registration.certificate_id}.",
                "CERTIFICATE",
                link=f"/events/certificate/{registration.certificate_id}/"
            )

        log_activity(
            request.user,
            'ATTENDEE_CHECKIN',
            f"Ticket Check-in: {registration.attendee_name}",
            f"Organizer checked in {registration.attendee_name} for '{registration.event.title}' (Ticket: {ticket_code}).",
            request=request
        )

        resp_data = {
            'success': True,
            'attendee_name': registration.attendee_name,
            'event_title': registration.event.title,
            'ticket_code': registration.ticket_code,
            'certificate_id': registration.certificate_id,
            'already_attended': already_attended,
            'message': f"Attendee '{registration.attendee_name}' checked in successfully!" if not already_attended else f"Attendee '{registration.attendee_name}' was already checked in."
        }

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse(resp_data)

        if already_attended:
            messages.info(request, f"Attendee {registration.attendee_name} was already verified as ATTENDED. Certificate ID: {registration.certificate_id}")
        else:
            messages.success(request, f"Check-in verified! {registration.attendee_name} marked as ATTENDED. Certificate issued: {registration.certificate_id}")

        return redirect('admin_ticket_scan')

    recent_attended = EventRegistration.objects.filter(attendance_status='ATTENDED').select_related('event').order_by('-certificate_issued_at')[:15]
    total_attended_all = EventRegistration.objects.filter(attendance_status='ATTENDED').count()
    total_rsvps = EventRegistration.objects.count()

    return render(request, 'events/admin_ticket_scanner.html', {
        'recent_attended': recent_attended,
        'total_attended_all': total_attended_all,
        'total_rsvps': total_rsvps,
    })

# --- ORGANIZER ADMIN EVENT MANAGEMENT ---

@login_required
@user_passes_test(is_organizer)
def admin_events_list_view(request):
    status_filter = request.GET.get('status', 'ALL')
    events = Event.objects.all().order_by('-start_datetime')

    if status_filter != 'ALL':
        events = events.filter(status=status_filter)

    # Statistics
    total_events = Event.objects.count()
    upcoming_count = Event.objects.filter(status__in=['OPEN', 'FULL']).count()
    completed_count = Event.objects.filter(status='COMPLETED').count()
    total_rsvps = EventRegistration.objects.count()

    context = {
        'events': events,
        'status_filter': status_filter,
        'total_events': total_events,
        'upcoming_count': upcoming_count,
        'completed_count': completed_count,
        'total_rsvps': total_rsvps,
        'categories': EventCategory.choices,
        'event_modes': EventMode.choices,
        'audience_roles': EventAudienceRole.choices,
        'resource_roles': ResourceAccessRole.choices,
    }
    return render(request, 'events/admin_events.html', context)

@login_required
@user_passes_test(is_organizer)
def admin_event_create_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', EventCategory.MEETUP)
        audience_role = request.POST.get('audience_role', EventAudienceRole.PUBLIC)
        start_datetime = request.POST.get('start_datetime')
        end_datetime = request.POST.get('end_datetime')
        venue = request.POST.get('venue', 'Hargeisa, Somaliland').strip()
        capacity = int(request.POST.get('capacity', 50))
        cover_image = request.FILES.get('cover_image')
        if cover_image:
            try:
                validate_uploaded_image(cover_image)
            except ValidationError as e:
                messages.error(request, f"Security Warning: {e.message}")
                return redirect('admin_event_create')

        cover_image_url = request.POST.get('cover_image_url', '').strip()
        status = request.POST.get('status', EventStatus.OPEN)

        event_mode = request.POST.get('event_mode', EventMode.IN_PERSON)
        meeting_url = request.POST.get('meeting_url', '').strip()
        meeting_platform = request.POST.get('meeting_platform', 'Zoom').strip()
        meeting_passcode = request.POST.get('meeting_passcode', '').strip()
        is_live_now = 'is_live_now' in request.POST

        event = Event.objects.create(
            title=title,
            description=description,
            category=category,
            audience_role=audience_role,
            event_mode=event_mode,
            meeting_url=meeting_url if meeting_url else None,
            meeting_platform=meeting_platform,
            meeting_passcode=meeting_passcode if meeting_passcode else None,
            is_live_now=is_live_now,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            venue=venue,
            capacity=capacity,
            registration_deadline=start_datetime,
            cover_image=cover_image if cover_image else None,
            cover_image_url=cover_image_url or ('/static/images/hub-hero.png' if not cover_image else ''),
            status=status,
            created_by=request.user
        )

        # Optional Resource Upload on creation
        resource_file = request.FILES.get('resource_file')
        resource_title = request.POST.get('resource_title', '').strip()
        access_role = request.POST.get('access_role', ResourceAccessRole.PUBLIC)
        is_members_only = (access_role != ResourceAccessRole.PUBLIC) or ('is_members_only' in request.POST)
        if resource_file:
            try:
                validate_uploaded_document(resource_file)
                EventResource.objects.create(
                    event=event,
                    title=resource_title or resource_file.name,
                    file=resource_file,
                    access_role=access_role,
                    is_members_only=is_members_only,
                    created_by=request.user
                )
            except ValidationError as e:
                messages.warning(request, f"Event created, but resource file skipped: {e.message}")

        log_activity(
            request.user,
            'EVENT_CREATED',
            f"Created Event: {event.title}",
            f"Organizer scheduled {event.category} '{event.title}' ({event.get_event_mode_display()} • {event.get_audience_role_display()}) at {event.venue}.",
            request=request
        )
        messages.success(request, f"Created new gathering: '{event.title}' successfully.")
        return redirect('admin_events')

    return redirect('admin_events')

@login_required
@user_passes_test(is_organizer)
def admin_event_edit_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        event.title = request.POST.get('title', '').strip()
        event.description = request.POST.get('description', '').strip()
        event.category = request.POST.get('category', EventCategory.MEETUP)
        event.audience_role = request.POST.get('audience_role', EventAudienceRole.PUBLIC)
        event.event_mode = request.POST.get('event_mode', EventMode.IN_PERSON)
        event.meeting_url = request.POST.get('meeting_url', '').strip() or None
        event.meeting_platform = request.POST.get('meeting_platform', 'Zoom').strip()
        event.meeting_passcode = request.POST.get('meeting_passcode', '').strip() or None
        event.is_live_now = 'is_live_now' in request.POST
        event.start_datetime = request.POST.get('start_datetime')
        event.end_datetime = request.POST.get('end_datetime')
        event.venue = request.POST.get('venue', 'Hargeisa, Somaliland').strip()
        event.capacity = int(request.POST.get('capacity', 50))
        event.status = request.POST.get('status', EventStatus.OPEN)

        # Upload cover image from computer with strict security validation
        new_cover = request.FILES.get('cover_image')
        if new_cover:
            try:
                validate_uploaded_image(new_cover)
                event.cover_image = new_cover
            except ValidationError as e:
                messages.error(request, f"Security Warning: {e.message}")
                return redirect('admin_event_edit', event_id=event.id)

        cover_url = request.POST.get('cover_image_url', '').strip()
        if cover_url:
            event.cover_image_url = cover_url

        event.save()

        # Handle Resource Upload during edit
        resource_file = request.FILES.get('resource_file')
        resource_title = request.POST.get('resource_title', '').strip()
        resource_type = request.POST.get('resource_type', EventResourceType.PDF)
        access_role = request.POST.get('access_role', ResourceAccessRole.PUBLIC)
        is_members_only = (access_role != ResourceAccessRole.PUBLIC) or ('is_members_only' in request.POST)
        if resource_file:
            try:
                validate_uploaded_document(resource_file)
                EventResource.objects.create(
                    event=event,
                    title=resource_title or resource_file.name,
                    file=resource_file,
                    resource_type=resource_type,
                    access_role=access_role,
                    is_members_only=is_members_only,
                    created_by=request.user
                )
                messages.success(request, f"Uploaded resource: {resource_title or resource_file.name}")
            except ValidationError as e:
                messages.error(request, f"Resource upload failed: {e.message}")

        log_activity(
            request.user,
            'EVENT_UPDATED',
            f"Updated Event: {event.title}",
            f"Organizer {request.user.email} updated event '{event.title}'.",
            request=request
        )
        messages.success(request, f"Event '{event.title}' updated successfully.")
        return redirect('admin_event_edit', event_id=event.id)

    resources = event.resources.all()
    total_downloads = sum(r.download_count for r in resources)
    feedbacks = event.feedbacks.select_related('registration').all()
    context = {
        'event': event,
        'categories': EventCategory.choices,
        'statuses': EventStatus.choices,
        'event_modes': EventMode.choices,
        'audience_roles': EventAudienceRole.choices,
        'resource_roles': ResourceAccessRole.choices,
        'resource_types': EventResourceType.choices,
        'resources': resources,
        'total_downloads': total_downloads,
        'feedbacks': feedbacks,
        'average_rating': event.average_rating,
        'feedback_count': event.feedback_count,
    }
    return render(request, 'events/admin_event_edit.html', context)

@login_required
@user_passes_test(is_organizer)
def admin_event_resource_upload_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        resource_file = request.FILES.get('resource_file')
        resource_title = request.POST.get('resource_title', '').strip()
        resource_type = request.POST.get('resource_type', EventResourceType.PDF)
        access_role = request.POST.get('access_role', ResourceAccessRole.PUBLIC)
        is_members_only = (access_role != ResourceAccessRole.PUBLIC) or ('is_members_only' in request.POST)

        if not resource_file:
            messages.error(request, "Please select a file to upload.")
            return redirect('admin_event_edit', event_id=event.id)

        try:
            validate_uploaded_document(resource_file)
            res = EventResource.objects.create(
                event=event,
                title=resource_title or resource_file.name,
                file=resource_file,
                resource_type=resource_type,
                access_role=access_role,
                is_members_only=is_members_only,
                created_by=request.user
            )
            log_activity(
                request.user,
                'RESOURCE_UPLOADED',
                f"Uploaded Resource: {res.title}",
                f"Uploaded '{res.title}' ({res.get_access_role_display()}) for event '{event.title}'.",
                request=request
            )
            messages.success(request, f"Uploaded resource '{res.title}' successfully.")
        except ValidationError as e:
            messages.error(request, f"Resource upload failed: {e.message}")

    return redirect('admin_event_edit', event_id=event.id)

@login_required
@user_passes_test(is_organizer)
def admin_event_resource_role_update_view(request, resource_id):
    res = get_object_or_404(EventResource, id=resource_id)
    if request.method == 'POST':
        new_role = request.POST.get('access_role', ResourceAccessRole.PUBLIC)
        if new_role in ResourceAccessRole.values:
            res.access_role = new_role
            res.save()
            messages.success(request, f"Updated access role for '{res.title}' to {res.get_access_role_display()}.")
    return redirect('admin_event_edit', event_id=res.event.id)

@login_required
@user_passes_test(is_organizer)
def admin_event_resource_delete_view(request, resource_id):
    resource = get_object_or_404(EventResource, id=resource_id)
    event_id = resource.event.id
    title = resource.title
    if request.method == 'POST':
        resource.delete()
        log_activity(
            request.user,
            'RESOURCE_DELETED',
            f"Deleted Resource: {title}",
            f"Organizer removed resource '{title}'.",
            request=request
        )
        messages.success(request, f"Resource '{title}' removed.")
    return redirect('admin_event_edit', event_id=event_id)

def event_resource_download_view(request, resource_id):
    """
    Secure tracked resource download endpoint.
    Verifies user permissions according to access_role,
    atomically increments download_count, and streams the file as an attachment.
    """
    res = get_object_or_404(EventResource, id=resource_id)

    # Determine membership context
    user_is_member = False
    if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile is not None:
        user_is_member = True

    ticket_code = request.GET.get('ticket', '').strip()
    if ticket_code:
        reg = EventRegistration.objects.filter(ticket_code__iexact=ticket_code, event=res.event).first()
        if reg and reg.is_community_member:
            user_is_member = True

    if not res.can_user_download(user=request.user, is_community_member=user_is_member):
        if res.access_role == ResourceAccessRole.MEMBER or res.is_members_only:
            messages.warning(request, f"'{res.title}' is exclusive to verified TechClub Community Members. Apply for membership to unlock.")
            return redirect('apply')
        messages.error(request, f"You do not have permission to download '{res.title}'.")
        return redirect('event_detail', event_id=res.event.id)

    if not res.file:
        raise Http404("Resource file is unavailable.")

    # Increment download counter atomically
    res.increment_download_count()

    if request.user.is_authenticated:
        log_activity(
            request.user,
            'RESOURCE_DOWNLOADED',
            f"Downloaded Material: {res.title}",
            f"User {request.user.email} downloaded '{res.title}' for '{res.event.title}' (Total downloads: {res.download_count}).",
            request=request
        )

    filename = os.path.basename(res.file.name)
    return FileResponse(res.file.open('rb'), as_attachment=True, filename=filename)

@login_required
@user_passes_test(is_organizer)
def admin_event_toggle_live_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        event.is_live_now = not event.is_live_now
        event.save()
        status_txt = "LIVE STREAM ACTIVE" if event.is_live_now else "Live Stream Ended"
        
        if event.is_live_now:
            # Broadcast notification to all confirmed attendees
            for reg in event.registrations.filter(status='REGISTERED'):
                if reg.member and reg.member.user:
                    notify_user(
                        reg.member.user,
                        f"🔴 LIVE NOW: {event.title}",
                        f"The online session for '{event.title}' has started! Click your ticket pass to join now.",
                        "EVENT",
                        link=f"/events/ticket/{reg.ticket_code}/"
                    )

        log_activity(
            request.user,
            'EVENT_LIVE_TOGGLED',
            f"Event Live Status: {status_txt}",
            f"Live session for '{event.title}' is now {'ON' if event.is_live_now else 'OFF'}.",
            request=request
        )
        messages.info(request, f"Event '{event.title}' live broadcast status is now: {status_txt}.")
    return redirect('admin_event_edit', event_id=event.id)

@login_required
@user_passes_test(is_organizer)
def admin_event_delete_view(request, event_id):
    if request.method == 'POST':
        event = get_object_or_404(Event, id=event_id)
        title = event.title
        log_activity(
            request.user,
            'EVENT_DELETED',
            f"Deleted Event: {title}",
            f"Organizer {request.user.email} permanently deleted event '{title}'.",
            request=request
        )
        event.delete()
        messages.success(request, f"Event '{title}' has been deleted successfully.")
    return redirect('admin_events')

@login_required
@user_passes_test(is_organizer)
def admin_attendance_view(request, event_id=None):
    if event_id:
        selected_event = get_object_or_404(Event, id=event_id)
    else:
        selected_event = Event.objects.order_by('-start_datetime').first()

    all_events = Event.objects.all().order_by('-start_datetime')
    registrations = selected_event.registrations.all() if selected_event else []

    context = {
        'selected_event': selected_event,
        'all_events': all_events,
        'registrations': registrations,
    }
    return render(request, 'events/admin_attendance.html', context)

@login_required
@user_passes_test(is_organizer)
def admin_attendance_toggle(request, reg_id):
    reg = get_object_or_404(EventRegistration, id=reg_id)
    new_status = request.POST.get('status')
    if new_status in ['ATTENDED', 'ABSENT', 'PENDING']:
        was_attended = (reg.attendance_status == 'ATTENDED')
        reg.attendance_status = new_status
        if new_status == 'ATTENDED':
            reg.issue_certificate_if_attended()
        reg.save()

        if new_status == 'ATTENDED' and not was_attended and reg.member and reg.member.user:
            notify_user(
                reg.member.user,
                f"🎓 Certificate Issued: {reg.event.title}",
                f"Congratulations! Your official certificate of attendance for '{reg.event.title}' is now ready. Certificate ID: {reg.certificate_id}.",
                "CERTIFICATE",
                link=f"/events/certificate/{reg.certificate_id}/"
            )

        messages.success(request, f"Updated attendance for {reg.attendee_name}: {reg.get_attendance_status_display()}")

    return redirect('admin_attendance_event', event_id=reg.event.id)

@login_required
@user_passes_test(is_organizer)
def admin_export_attendance_csv(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_{event.id}_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Event Title', 'Attendee Name', 'Attendee Email', 'Phone', 'Registration Status', 'Attendance Status', 'Registered At'])

    for r in event.registrations.all():
        writer.writerow([
            event.title, r.attendee_name, r.attendee_email, r.attendee_phone,
            r.status, r.attendance_status, r.registered_at.strftime('%Y-%m-%d %H:%M')
        ])

    return response


# --- ENHANCEMENTS: CALENDAR, CANCELLATION & FEEDBACK ---

def event_calendar_ics_view(request, event_id):
    """
    Generate standard RFC 5545 iCalendar (.ics) file for Apple Calendar, Outlook, and other desktop/mobile apps.
    """
    import datetime
    event = get_object_or_404(Event, id=event_id)
    start_utc = event.start_datetime.astimezone(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    end_utc = event.end_datetime.astimezone(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dtstamp = timezone.now().astimezone(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')

    location = event.venue
    description = (event.description or "").replace("\r\n", "\\n").replace("\n", "\\n")
    if event.is_online and event.meeting_url:
        location = event.meeting_url
        description += f"\\n\\nVirtual Classroom: {event.meeting_url}"
        if event.meeting_passcode:
            description += f"\\nPasscode / PIN: {event.meeting_passcode}"

    slug = "".join(c if c.isalnum() else "_" for c in event.title).strip("_")[:40]

    ics_content = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//TechClub//Events Calendar//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:tc-evt-{event.id}-{dtstamp}@techclub.so\r\n"
        f"DTSTAMP:{dtstamp}\r\n"
        f"DTSTART:{start_utc}\r\n"
        f"DTEND:{end_utc}\r\n"
        f"SUMMARY:{event.title}\r\n"
        f"DESCRIPTION:{description}\r\n"
        f"LOCATION:{location}\r\n"
        f"STATUS:CONFIRMED\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )

    response = HttpResponse(ics_content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{slug}.ics"'
    return response


def event_ticket_cancel_view(request, ticket_code):
    """
    Self-Service RSVP Cancellation with Automated Priority Waitlist Promotion.
    1. Validates ticket.
    2. Updates registration status to 'CANCELLED'.
    3. Finds earliest waitlisted attendee and promotes them to 'REGISTERED'.
    4. Notifies promoted attendee and logs activities.
    """
    if request.method != 'POST':
        return redirect('event_ticket', ticket_code=ticket_code)

    registration = get_object_or_404(EventRegistration, ticket_code__iexact=ticket_code.strip())
    event = registration.event

    if registration.attendance_status == 'ATTENDED':
        messages.error(request, "This pass has already been verified as attended and cannot be cancelled.")
        return redirect('event_ticket', ticket_code=ticket_code)

    if registration.status == 'CANCELLED':
        messages.info(request, "This RSVP has already been cancelled.")
        return redirect('event_ticket', ticket_code=ticket_code)

    # Cancel current registration
    registration.status = 'CANCELLED'
    registration.save()

    log_activity(
        request.user if request.user.is_authenticated else None,
        'EVENT_RSVP_CANCELLED',
        f"Cancelled RSVP: {event.title}",
        f"{registration.attendee_name} cancelled their RSVP for '{event.title}'.",
        request=request
    )

    promoted_msg = ""
    # Check for attendees on the Priority Waitlist to automatically promote
    next_waitlisted = EventRegistration.objects.filter(
        event=event,
        status='WAITLISTED'
    ).order_by('registered_at').first()

    if next_waitlisted:
        next_waitlisted.status = 'REGISTERED'
        next_waitlisted.save()

        # If event was marked FULL, check capacity
        if not event.is_full and event.status == EventStatus.FULL:
            event.status = EventStatus.OPEN
            event.save()

        # Notify promoted attendee
        try:
            send_event_registration_confirmation(next_waitlisted, request)
        except Exception:
            pass

        if next_waitlisted.member and next_waitlisted.member.user:
            notify_user(
                next_waitlisted.member.user,
                f"🎉 Seat Confirmed: {event.title}",
                f"Great news! A seat opened up for '{event.title}', and you have been automatically promoted from the waitlist to Confirmed Registration. Your digital ticket pass is active.",
                "EVENT",
                link=f"/events/ticket/{next_waitlisted.ticket_code}/"
            )

        log_activity(
            next_waitlisted.member.user if next_waitlisted.member else None,
            'WAITLIST_PROMOTED',
            f"Promoted to Confirmed: {event.title}",
            f"{next_waitlisted.attendee_name} was automatically promoted from the Priority Waitlist to Confirmed Registration for '{event.title}'.",
            request=request
        )
        promoted_msg = f" Your seat was automatically transferred to {next_waitlisted.attendee_name} on the priority waitlist."

    messages.success(request, f"Your RSVP for '{event.title}' has been successfully cancelled.{promoted_msg}")
    return redirect('event_ticket', ticket_code=ticket_code)


def event_submit_feedback_view(request, ticket_code):
    """
    Post-Event Satisfaction Rating & Review Submission.
    Only available to verified attendees (attendance_status == 'ATTENDED').
    """
    if request.method != 'POST':
        return redirect('event_ticket', ticket_code=ticket_code)

    registration = get_object_or_404(EventRegistration, ticket_code__iexact=ticket_code.strip())
    event = registration.event

    if registration.attendance_status != 'ATTENDED':
        messages.error(request, "Only verified attendees who checked in to this event can submit a rating and feedback.")
        return redirect('event_ticket', ticket_code=ticket_code)

    try:
        rating_val = int(request.POST.get('rating', 5))
        rating_val = max(1, min(5, rating_val))
    except (ValueError, TypeError):
        rating_val = 5

    feedback_text = request.POST.get('feedback_text', '').strip()

    feedback, created = EventFeedback.objects.update_or_create(
        event=event,
        registration=registration,
        defaults={
            'rating': rating_val,
            'feedback_text': feedback_text,
        }
    )

    action_word = "submitted" if created else "updated"
    messages.success(request, f"Thank you! Your {rating_val}-star review has been {action_word} successfully.")

    log_activity(
        request.user if request.user.is_authenticated else None,
        'EVENT_FEEDBACK_SUBMITTED',
        f"Rated Event: {event.title} ({rating_val}★)",
        f"{registration.attendee_name} rated '{event.title}' {rating_val} stars.",
        request=request
    )

    return redirect('event_ticket', ticket_code=ticket_code)

