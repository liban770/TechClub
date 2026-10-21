from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Avg
from django.utils import timezone
from django.core.management import call_command
from django.http import HttpResponse
import io
from applications.models import Application, ApplicationStatus, ReferralSource, DisciplineCategory
from members.models import MemberProfile, Skill
from events.models import Event, EventRegistration, EventFeedback
from meetings.models import Meeting
from announcements.models import Announcement, PublicationStatus
from accounts.models import User, UserRole, UserActivity, log_activity, notify_user

from django.core.exceptions import ValidationError
from techclub_core.validators import validate_uploaded_image
from django.contrib import messages
from .models import PartnershipInquiry, FounderProfile, CorporatePartner, PartnerTier, PartnerStatus

def is_organizer(user):
    return user.is_authenticated and user.is_organizer

# --- PUBLIC PAGES ---

def home_view(request):
    featured_events = Event.objects.filter(status='OPEN').order_by('start_datetime')[:3]
    featured_members = MemberProfile.objects.exclude(profile_visibility='PRIVATE').prefetch_related('skills').order_by('-is_mentor')[:6]
    announcements = Announcement.objects.filter(publication_status=PublicationStatus.PUBLISHED)[:3]

    total_members = MemberProfile.objects.count()
    total_events = Event.objects.count()
    founder = FounderProfile.get_solo()

    # Corporate Partners & Trust Endorsements for Homepage
    approved_partners = CorporatePartner.objects.filter(status=PartnerStatus.APPROVED, is_published=True, is_featured_home=True).order_by('display_order', '-created_at')[:8]
    featured_chairman_quotes = [p for p in approved_partners if p.chairman_quote.strip()][:3]

    context = {
        'featured_events': featured_events,
        'featured_members': featured_members,
        'announcements': announcements,
        'total_members': total_members,
        'total_events': total_events,
        'founder': founder,
        'approved_partners': approved_partners,
        'featured_chairman_quotes': featured_chairman_quotes,
    }
    return render(request, 'public/home.html', context)

def about_view(request):
    founder = FounderProfile.get_solo()
    return render(request, 'public/about.html', {'founder': founder})

def founder_view(request):
    founder = FounderProfile.get_solo()

    if request.method == 'POST':
        org_name = request.POST.get('organization_name', '').strip()
        contact_name = request.POST.get('contact_name', '').strip()
        email = request.POST.get('email', '').strip()
        interests = request.POST.getlist('partnership_interests')
        message_body = request.POST.get('message', '').strip()

        if org_name and contact_name and email and message_body:
            PartnershipInquiry.objects.create(
                organization_name=org_name,
                contact_name=contact_name,
                email=email,
                partnership_interests=", ".join(interests) if interests else "General Collaboration",
                message=message_body
            )
            messages.success(
                request,
                f"Thank you, {contact_name}. Your partnership inquiry on behalf of '{org_name}' has been received. Our leadership and founder {founder.full_name} will review your proposal and get in touch."
            )
        else:
            messages.error(request, "Please fill in all required fields before submitting your partnership inquiry.")
        return redirect('founder')

    return render(request, 'public/founder.html', {'founder': founder})

def code_of_conduct_view(request):
    return render(request, 'public/code_of_conduct.html')

# --- ORGANIZER ADMIN OVERVIEW & SYSTEM ANALYTICS ---

@login_required
@user_passes_test(is_organizer)
def admin_overview_view(request):
    # 1. Community & Membership Analytics
    total_members = MemberProfile.objects.count()
    total_users = User.objects.count()
    total_mentors = MemberProfile.objects.filter(is_mentor=True).count()

    role_counts = {
        'organizers': User.objects.filter(role=UserRole.ORGANIZER).count(),
        'members': User.objects.filter(role=UserRole.MEMBER).count(),
        'applicants': User.objects.filter(role=UserRole.APPLICANT).count(),
        'superusers': User.objects.filter(is_superuser=True).count(),
    }

    # 2. Admissions Funnel Analytics
    total_applications = Application.objects.count()
    pending_apps = Application.objects.filter(status=ApplicationStatus.PENDING).count()
    approved_apps = Application.objects.filter(status=ApplicationStatus.APPROVED).count()
    waitlisted_apps = Application.objects.filter(status=ApplicationStatus.WAITLISTED).count()
    rejected_apps = Application.objects.filter(status=ApplicationStatus.REJECTED).count()
    acceptance_rate = round((approved_apps / total_applications * 100), 1) if total_applications > 0 else 0

    recent_applications = Application.objects.all().order_by('-created_at')[:6]

    # Referral channel telemetry
    referral_stats = Application.objects.values('referral_source').annotate(total=Count('id')).order_by('-total')

    # Domain breakdown & Technical Disciplines
    raw_disciplines = MemberProfile.objects.values('discipline').annotate(total=Count('id')).order_by('-total')[:5]
    if raw_disciplines.exists():
        discipline_stats = [{'name': d.get('discipline') or 'General Tech', 'total': d['total']} for d in raw_disciplines]
    else:
        app_disciplines = Application.objects.values('professional_category').annotate(total=Count('id')).order_by('-total')[:5]
        discipline_stats = [{'name': d.get('professional_category') or 'General Tech', 'total': d['total']} for d in app_disciplines]

    experience_stats = MemberProfile.objects.values('experience_level').annotate(total=Count('id')).order_by('-total')

    # 3. Events, Attendance & Learning Outcomes
    total_events = Event.objects.count()
    upcoming_events = Event.objects.filter(status='OPEN').count()
    completed_events = Event.objects.filter(status='COMPLETED').count()
    upcoming_event_list = Event.objects.filter(status__in=['OPEN', 'FULL']).order_by('start_datetime')[:3]

    total_rsvps = EventRegistration.objects.count()
    total_checkins = EventRegistration.objects.filter(attendance_status='ATTENDED').count()
    total_certificates = EventRegistration.objects.filter(
        attendance_status='ATTENDED', 
        certificate_id__isnull=False
    ).exclude(certificate_id='').count()
    attendance_rate = round((total_checkins / total_rsvps * 100), 1) if total_rsvps > 0 else 0

    # Attendee Feedback & Satisfaction Ratings
    total_feedbacks = EventFeedback.objects.count()
    avg_satisfaction_raw = EventFeedback.objects.aggregate(avg=Avg('rating'))['avg']
    avg_satisfaction = round(avg_satisfaction_raw, 1) if avg_satisfaction_raw else None

    # 4. Meetings & Mentorship
    total_meetings = Meeting.objects.count()
    completed_meetings = Meeting.objects.filter(status='COMPLETED').count()

    # 5. Live Streams & Partnerships
    recent_activities = UserActivity.objects.all().order_by('-created_at')[:8]
    partnership_inquiries = PartnershipInquiry.objects.all().order_by('-created_at')[:6]
    pending_inquiries_count = PartnershipInquiry.objects.filter(is_reviewed=False).count()

    context = {
        'total_members': total_members,
        'total_users': total_users,
        'total_mentors': total_mentors,
        'role_counts': role_counts,
        'total_applications': total_applications,
        'pending_apps': pending_apps,
        'approved_apps': approved_apps,
        'waitlisted_apps': waitlisted_apps,
        'rejected_apps': rejected_apps,
        'acceptance_rate': acceptance_rate,
        'upcoming_events': upcoming_events,
        'completed_events': completed_events,
        'total_events': total_events,
        'total_rsvps': total_rsvps,
        'total_checkins': total_checkins,
        'total_certificates': total_certificates,
        'attendance_rate': attendance_rate,
        'total_feedbacks': total_feedbacks,
        'avg_satisfaction': avg_satisfaction,
        'total_meetings': total_meetings,
        'completed_meetings': completed_meetings,
        'recent_applications': recent_applications,
        'upcoming_event_list': upcoming_event_list,
        'referral_stats': referral_stats,
        'discipline_stats': discipline_stats,
        'experience_stats': experience_stats,
        'recent_activities': recent_activities,
        'partnership_inquiries': partnership_inquiries,
        'pending_inquiries_count': pending_inquiries_count,
    }
    return render(request, 'dashboard/admin_overview.html', context)

@login_required
@user_passes_test(is_organizer)
def admin_inquiry_toggle_view(request, inquiry_id):
    from django.shortcuts import get_object_or_404
    inquiry = get_object_or_404(PartnershipInquiry, id=inquiry_id)
    inquiry.is_reviewed = not inquiry.is_reviewed
    inquiry.save()
    status_str = "Reviewed" if inquiry.is_reviewed else "Pending"
    messages.info(request, f"Inquiry from '{inquiry.organization_name}' marked as {status_str}.")
    return redirect('admin_overview')

@login_required
@user_passes_test(is_organizer)
def admin_founder_manage_view(request):
    founder = FounderProfile.get_solo()

    if request.method == 'POST':
        founder.full_name = request.POST.get('full_name', '').strip()
        founder.title = request.POST.get('title', '').strip()
        founder.headline = request.POST.get('headline', '').strip()
        founder.education = request.POST.get('education', '').strip()
        founder.graduation_year = request.POST.get('graduation_year', '').strip()
        founder.cgpa = request.POST.get('cgpa', '').strip()
        founder.university_role = request.POST.get('university_role', '').strip()
        founder.linkedin_url = request.POST.get('linkedin_url', '').strip()
        founder.biography = request.POST.get('biography', '').strip()
        founder.central_message = request.POST.get('central_message', '').strip()
        founder.story_subheading = request.POST.get('story_subheading', '').strip()
        founder.story_body = request.POST.get('story_body', '').strip()
        founder.personal_message = request.POST.get('personal_message', '').strip()

        # Handle photo upload from computer with strict security validation
        new_photo = request.FILES.get('photo')
        if new_photo:
            try:
                validate_uploaded_image(new_photo)
                founder.photo = new_photo
            except ValidationError as e:
                messages.error(request, f"Security Warning: {e.message}")
                return redirect('admin_founder_manage')

        custom_photo_url = request.POST.get('photo_url', '').strip()
        if custom_photo_url:
            founder.photo_url = custom_photo_url

        founder.save()

        log_activity(
            request.user,
            'FOUNDER_PROFILE_UPDATED',
            f"Updated Founder Profile: {founder.full_name}",
            f"Organizer {request.user.email} updated the Meet the Founder profile & portrait photo.",
            request=request
        )
        messages.success(request, "Meet the Founder profile and portrait photo have been updated successfully.")
        return redirect('admin_founder_manage')

    context = {
        'founder': founder,
    }
    return render(request, 'dashboard/admin_founder_manage.html', context)

@login_required
@user_passes_test(is_organizer)
def admin_reports_view(request):
    total_apps = Application.objects.count()
    status_counts = Application.objects.values('status').annotate(total=Count('id'))
    referral_stats = Application.objects.values('referral_source').annotate(total=Count('id')).order_by('-total')
    discipline_stats = MemberProfile.objects.values('discipline').annotate(total=Count('id')).order_by('-total')
    experience_stats = MemberProfile.objects.values('experience_level').annotate(total=Count('id')).order_by('-total')

    total_reg = EventRegistration.objects.count()
    attended_reg = EventRegistration.objects.filter(attendance_status='ATTENDED').count()
    attendance_rate = round((attended_reg / total_reg * 100), 1) if total_reg > 0 else 0

    context = {
        'total_apps': total_apps,
        'status_counts': status_counts,
        'referral_stats': referral_stats,
        'discipline_stats': discipline_stats,
        'experience_stats': experience_stats,
        'total_reg': total_reg,
        'attended_reg': attended_reg,
        'attendance_rate': attendance_rate,
    }
    return render(request, 'dashboard/admin_reports.html', context)

@login_required
@user_passes_test(is_organizer)
def admin_backup_download_view(request):
    """
    1-Click Founder Database Backup:
    Generates a full JSON snapshot of all system models (accounts, applications, members,
    events, tickets, certificates, meetings, announcements, dashboard) and streams it as a download.
    """
    buffer = io.StringIO()
    call_command(
        'dumpdata',
        'accounts',
        'applications',
        'members',
        'events',
        'meetings',
        'announcements',
        'dashboard',
        natural_foreign=True,
        natural_primary=True,
        indent=2,
        stdout=buffer
    )
    backup_data = buffer.getvalue()
    timestamp = timezone.now().strftime('%Y-%m-%d_%H%M')
    filename = f"techclub_backup_{timestamp}.json"

    log_activity(
        request.user,
        'BACKUP_DOWNLOADED',
        "Founder Full Database Backup Exported",
        f"Organizer {request.user.email} generated and downloaded a full JSON database snapshot ({len(backup_data)} bytes).",
        request=request
    )

    response = HttpResponse(backup_data, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# --- MEMBER DASHBOARD ---

@login_required
def member_dashboard_view(request):
    profile, _ = MemberProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': request.user.get_full_name() or request.user.username,
        }
    )

    # 1. Events & Gathering Analytics
    all_registrations = EventRegistration.objects.filter(
        attendee_email__iexact=request.user.email
    ).select_related('event').order_by('-registered_at')

    total_rsvps = all_registrations.count()
    attended_count = all_registrations.filter(attendance_status='ATTENDED').count()
    certificates_earned = all_registrations.filter(
        attendance_status='ATTENDED', 
        certificate_id__isnull=False
    ).exclude(certificate_id='')
    certificates_count = certificates_earned.count()
    
    # Attendance Rate calculation
    attendance_rate = round((attended_count / total_rsvps * 100)) if total_rsvps > 0 else 0

    # 2. Meetings & Mentorship Analytics
    my_meetings = Meeting.objects.filter(participants__member=profile).order_by('start_datetime')
    total_meetings = my_meetings.count()
    completed_meetings = my_meetings.filter(status='COMPLETED').count()

    # 3. Profile Completion Telemetry (0 - 100%)
    completion_points = 0
    if profile.full_name: completion_points += 15
    if profile.professional_title: completion_points += 15
    if profile.bio: completion_points += 15
    if profile.profile_photo or profile.avatar_url: completion_points += 20
    if profile.skills.exists(): completion_points += 15
    if profile.github_url or profile.linkedin_url or profile.portfolio_url: completion_points += 20
    profile_completion = min(100, completion_points)

    announcements = Announcement.objects.filter(publication_status=PublicationStatus.PUBLISHED)[:5]
    upcoming_events = Event.objects.filter(status='OPEN').order_by('start_datetime')[:3]
    my_activities = UserActivity.objects.filter(user=request.user).order_by('-created_at')[:6]

    context = {
        'profile': profile,
        'my_registrations': all_registrations,
        'total_rsvps': total_rsvps,
        'attended_count': attended_count,
        'certificates_count': certificates_count,
        'certificates_earned': certificates_earned,
        'attendance_rate': attendance_rate,
        'my_meetings': my_meetings,
        'total_meetings': total_meetings,
        'completed_meetings': completed_meetings,
        'profile_completion': profile_completion,
        'skills_count': profile.skills.count(),
        'announcements': announcements,
        'upcoming_events': upcoming_events,
        'my_activities': my_activities,
    }
    return render(request, 'dashboard/member_dashboard.html', context)


# --- CORPORATE PARTNERS & TRUST VIEWS ---

def partners_list_view(request):
    all_approved = list(CorporatePartner.objects.filter(status=PartnerStatus.APPROVED, is_published=True).order_by('display_order', '-created_at'))

    strategic_partners = [p for p in all_approved if p.tier == PartnerTier.STRATEGIC]
    premier_partners = [p for p in all_approved if p.tier == PartnerTier.PREMIER]
    ecosystem_partners = [p for p in all_approved if p.tier == PartnerTier.ECOSYSTEM]
    community_supporters = [p for p in all_approved if p.tier == PartnerTier.COMMUNITY]

    chairman_endorsements = [p for p in all_approved if p.chairman_quote.strip()]

    context = {
        'all_partners': all_approved,
        'strategic_partners': strategic_partners,
        'premier_partners': premier_partners,
        'ecosystem_partners': ecosystem_partners,
        'community_supporters': community_supporters,
        'chairman_endorsements': chairman_endorsements,
        'total_partners_count': len(all_approved),
        'tiers': PartnerTier.choices,
    }
    return render(request, 'partners/partners_list.html', context)


def partner_apply_view(request):
    if request.method == 'POST':
        # Anti-bot Honeypot trap: if filled by automated bot, ignore quietly
        honeypot = request.POST.get('company_security_check_hp', '').strip()
        if honeypot:
            messages.success(request, "Your partnership proposal has been received.")
            return redirect('partners')

        company_name = request.POST.get('company_name', '').strip()
        industry = request.POST.get('industry', '').strip() or 'Technology & Telecommunications'
        website_url = request.POST.get('website_url', '').strip()
        tier = request.POST.get('tier', PartnerTier.ECOSYSTEM)

        chairman_name = request.POST.get('chairman_name', '').strip()
        chairman_title = request.POST.get('chairman_title', '').strip()
        chairman_quote = request.POST.get('chairman_quote', '').strip()
        chairman_linkedin = request.POST.get('chairman_linkedin', '').strip()

        contact_person_name = request.POST.get('contact_person_name', '').strip()
        contact_email = request.POST.get('contact_email', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()
        partnership_offering = request.POST.get('partnership_offering', '').strip()

        logo_file = request.FILES.get('logo')
        chairman_photo_file = request.FILES.get('chairman_photo')

        if not (company_name and website_url and chairman_name and chairman_title and contact_person_name and contact_email):
            messages.error(request, "Please fill in all required company and executive leadership fields.")
            return render(request, 'partners/partner_apply.html', {'tiers': PartnerTier.choices})

        # Validate uploads if provided
        if logo_file:
            try:
                validate_uploaded_image(logo_file, max_size_mb=4)
            except ValidationError as e:
                messages.error(request, f"Company logo error: {e.message}")
                return render(request, 'partners/partner_apply.html', {'tiers': PartnerTier.choices})

        if chairman_photo_file:
            try:
                validate_uploaded_image(chairman_photo_file, max_size_mb=4)
            except ValidationError as e:
                messages.error(request, f"Chairman photo error: {e.message}")
                return render(request, 'partners/partner_apply.html', {'tiers': PartnerTier.choices})

        partner = CorporatePartner.objects.create(
            company_name=company_name,
            industry=industry,
            website_url=website_url,
            tier=tier,
            status=PartnerStatus.PENDING,
            is_published=False,
            chairman_name=chairman_name,
            chairman_title=chairman_title,
            chairman_quote=chairman_quote,
            chairman_linkedin=chairman_linkedin,
            contact_person_name=contact_person_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            partnership_offering=partnership_offering,
            logo=logo_file,
            chairman_photo=chairman_photo_file,
        )

        log_activity(
            user=request.user if request.user.is_authenticated else None,
            activity_type="PARTNER_APPLICATION_SUBMITTED",
            title=f"Corporate proposal received from {company_name}",
            description=f"Corporate sponsorship proposal received from '{company_name}' ({tier}). Contact: {contact_person_name} ({contact_email}).",
            request=request
        )

        for admin_user in User.objects.filter(is_superuser=True):
            notify_user(
                user=admin_user,
                title="New Corporate Sponsorship Proposal",
                message=f"'{company_name}' submitted a partnership request ({tier}) with Chairman endorsement by {chairman_name}.",
                link="/admin-ops/partners/",
                notification_type="APPLICATION"
            )

        messages.success(
            request,
            f"Thank you, {contact_person_name}. Your corporate partnership proposal on behalf of '{company_name}' has been successfully submitted! Our leadership team will review the executive endorsement and reach out shortly."
        )
        return redirect('partners')

    return render(request, 'partners/partner_apply.html', {'tiers': PartnerTier.choices})


@login_required
@user_passes_test(is_organizer)
def admin_partners_manage_view(request):
    status_filter = request.GET.get('status', 'ALL')
    partners = CorporatePartner.objects.all().order_by('display_order', '-created_at')

    if status_filter != 'ALL':
        partners = partners.filter(status=status_filter)

    total_count = CorporatePartner.objects.count()
    pending_count = CorporatePartner.objects.filter(status=PartnerStatus.PENDING).count()
    review_count = CorporatePartner.objects.filter(status=PartnerStatus.UNDER_REVIEW).count()
    approved_count = CorporatePartner.objects.filter(status=PartnerStatus.APPROVED).count()

    context = {
        'partners': partners,
        'status_filter': status_filter,
        'total_count': total_count,
        'pending_count': pending_count,
        'review_count': review_count,
        'approved_count': approved_count,
        'statuses': PartnerStatus.choices,
        'tiers': PartnerTier.choices,
    }
    return render(request, 'dashboard/admin_partners.html', context)


@login_required
@user_passes_test(is_organizer)
def admin_partner_status_view(request, partner_id, new_status):
    partner = get_object_or_404(CorporatePartner, id=partner_id)
    if request.method == 'POST':
        if new_status in PartnerStatus.values:
            partner.status = new_status
            if new_status == PartnerStatus.APPROVED:
                partner.is_published = True
                partner.reviewed_at = timezone.now()
                partner.reviewed_by = request.user
                messages.success(request, f"Partner '{partner.company_name}' has been APPROVED and is now live on the public website and homepage!")
            elif new_status == PartnerStatus.UNDER_REVIEW:
                messages.info(request, f"Partner '{partner.company_name}' marked as UNDER REVIEW.")
            elif new_status == PartnerStatus.REJECTED:
                partner.is_published = False
                messages.warning(request, f"Partner '{partner.company_name}' proposal declined.")
            partner.save()

            log_activity(
                user=request.user,
                activity_type=f"PARTNER_{new_status}",
                title=f"Partner '{partner.company_name}' set to {new_status}",
                description=f"Organizer {request.user.username} set status of partner '{partner.company_name}' to {new_status}.",
                request=request
            )
    return redirect('admin_partners')


@login_required
@user_passes_test(is_organizer)
def admin_partner_edit_view(request, partner_id):
    partner = get_object_or_404(CorporatePartner, id=partner_id)
    if request.method == 'POST':
        partner.tier = request.POST.get('tier', partner.tier)
        partner.display_order = int(request.POST.get('display_order', partner.display_order) or 0)
        partner.is_published = request.POST.get('is_published') == '1'
        partner.is_featured_home = request.POST.get('is_featured_home') == '1'
        partner.chairman_name = request.POST.get('chairman_name', partner.chairman_name).strip()
        partner.chairman_title = request.POST.get('chairman_title', partner.chairman_title).strip()
        partner.chairman_quote = request.POST.get('chairman_quote', partner.chairman_quote).strip()
        partner.admin_notes = request.POST.get('admin_notes', partner.admin_notes).strip()
        partner.save()
        messages.success(request, f"Updated partner settings for '{partner.company_name}'.")
        return redirect('admin_partners')
    return render(request, 'dashboard/admin_partner_edit.html', {'partner': partner, 'tiers': PartnerTier.choices, 'statuses': PartnerStatus.choices})


@login_required
@user_passes_test(is_organizer)
def admin_partner_delete_view(request, partner_id):
    partner = get_object_or_404(CorporatePartner, id=partner_id)
    if request.method == 'POST':
        company_name = partner.company_name
        partner.delete()
        log_activity(
            user=request.user,
            activity_type="PARTNER_DELETED",
            title=f"Partner '{company_name}' deleted",
            description=f"Organizer {request.user.username} permanently deleted corporate partner '{company_name}'.",
            request=request
        )
        messages.success(request, f"Corporate partner '{company_name}' has been permanently deleted.")
    return redirect('admin_partners')

