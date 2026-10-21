import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from .models import Application, ApplicationStatus, ReferralSource, ExperienceLevel, DisciplineCategory, NotificationLog
from .emails import send_application_confirmation, send_approval_notification, send_status_update_notification
from accounts.models import User, UserRole, log_activity, notify_user
from members.models import MemberProfile, Skill

def is_organizer(user):
    return user.is_authenticated and user.is_organizer

# --- PUBLIC VIEWS ---

def apply_view(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        city = request.POST.get('city', 'Hargeisa').strip()
        current_role = request.POST.get('current_role', '').strip()
        professional_category = request.POST.get('professional_category', DisciplineCategory.SOFTWARE_ENG)
        organization = request.POST.get('organization', '').strip()
        experience_level = request.POST.get('experience_level', ExperienceLevel.JUNIOR)
        skills = request.POST.get('skills', '').strip()
        profile_summary = request.POST.get('profile_summary', '').strip()
        interests = ", ".join(request.POST.getlist('interests'))
        referral_source = request.POST.get('referral_source', ReferralSource.WHATSAPP)
        def clean_url(u):
            val = (u or '').strip()
            if val and not (val.startswith('http://') or val.startswith('https://')):
                return f'https://{val}'
            return val

        github_url = clean_url(request.POST.get('github_url', ''))
        linkedin_url = clean_url(request.POST.get('linkedin_url', ''))
        portfolio_url = clean_url(request.POST.get('portfolio_url', ''))

        if not full_name or not email or not phone or not current_role:
            messages.error(request, "Please fill in all required fields (Full Name, Email, Phone, and Current Role).")
            return redirect('apply')

        # 1. Check if user already exists
        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user:
            if not existing_user.is_active:
                messages.error(request, "Your TechClub account is currently deactivated. Please contact organizers at community@techclub.so for assistance.")
                return redirect('login')
            messages.info(request, "You already have an active TechClub member account. Please sign in to access your dashboard.")
            return redirect('login')

        # 2. Check if an application already exists with this email
        existing_app = Application.objects.filter(email__iexact=email).first()
        if existing_app:
            if existing_app.status == ApplicationStatus.PENDING:
                messages.warning(request, "You have already submitted an application and it is currently pending review by organizers. We will notify you via email and WhatsApp.")
                return redirect('application_success')
            elif existing_app.status == ApplicationStatus.APPROVED:
                messages.info(request, "Your membership application has already been approved! Please sign in with your credentials.")
                return redirect('login')
            elif existing_app.status == ApplicationStatus.WAITLISTED:
                messages.warning(request, "Your application is currently on the priority waiting list for upcoming cohorts. No need to re-apply.")
                return redirect('application_success')
            elif existing_app.status == ApplicationStatus.REJECTED:
                messages.error(request, "A previous application with this email address was reviewed and not accepted for this cycle.")
                return redirect('home')

        # 3. Check if phone number is already registered or pending
        existing_phone_app = Application.objects.filter(phone=phone, status=ApplicationStatus.PENDING).first()
        if existing_phone_app:
            messages.warning(request, f"An application using phone number '{phone}' is already pending review.")
            return redirect('application_success')

        app = Application.objects.create(
            full_name=full_name,
            email=email,
            phone=phone,
            city=city,
            current_role=current_role,
            professional_category=professional_category,
            organization=organization,
            experience_level=experience_level,
            skills=skills,
            profile_summary=profile_summary,
            interests=interests,
            referral_source=referral_source,
            github_url=github_url,
            linkedin_url=linkedin_url,
            portfolio_url=portfolio_url,
            status=ApplicationStatus.PENDING,
        )

        # Dispatch confirmation email safely
        try:
            send_application_confirmation(app, request)
        except Exception:
            pass

        log_activity(
            None,
            'APPLICATION_SUBMITTED',
            f"New Application: {app.full_name}",
            f"{app.full_name} ({app.email}) applied for {app.current_role} track via {app.referral_source}.",
            request=request
        )

        messages.success(request, f"Application successfully submitted! A confirmation has been sent to {app.email}.")
        request.session['last_applicant_name'] = app.full_name
        request.session['last_applicant_email'] = app.email
        return redirect('application_success')

    context = {
        'referral_sources': ReferralSource.choices,
        'experience_levels': ExperienceLevel.choices,
        'categories': DisciplineCategory.choices,
    }
    return render(request, 'applications/apply.html', context)

def application_success_view(request):
    applicant_name = request.session.get('last_applicant_name', 'Tech Explorer')
    applicant_email = request.session.get('last_applicant_email', 'your email')
    return render(request, 'applications/apply_success.html', {
        'applicant_name': applicant_name,
        'applicant_email': applicant_email,
    })

# --- ORGANIZER ADMIN VIEWS ---

@login_required
@user_passes_test(is_organizer)
def admin_applications_list_view(request):
    status_filter = request.GET.get('status', 'ALL')
    domain_filter = request.GET.get('domain', 'ALL')
    search_query = request.GET.get('q', '').strip()

    applications = Application.objects.all().order_by('-created_at')

    if status_filter != 'ALL':
        applications = applications.filter(status=status_filter)

    if domain_filter != 'ALL':
        applications = applications.filter(professional_category=domain_filter)

    if search_query:
        applications = applications.filter(
            full_name__icontains=search_query
        ) | applications.filter(
            email__icontains=search_query
        ) | applications.filter(
            skills__icontains=search_query
        ) | applications.filter(
            current_role__icontains=search_query
        )

    # Telemetry metrics
    total_count = Application.objects.count()
    pending_count = Application.objects.filter(status=ApplicationStatus.PENDING).count()
    waitlisted_count = Application.objects.filter(status=ApplicationStatus.WAITLISTED).count()
    approved_count = Application.objects.filter(status=ApplicationStatus.APPROVED).count()
    rejected_count = Application.objects.filter(status=ApplicationStatus.REJECTED).count()

    context = {
        'applications': applications,
        'status_filter': status_filter,
        'domain_filter': domain_filter,
        'search_query': search_query,
        'total_count': total_count,
        'pending_count': pending_count,
        'waitlisted_count': waitlisted_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'categories': DisciplineCategory.choices,
    }
    return render(request, 'applications/admin_applications.html', context)

@login_required
@user_passes_test(is_organizer)
def admin_application_detail_json(request, app_id):
    app = get_object_or_404(Application, id=app_id)
    return JsonResponse({
        'id': app.id,
        'full_name': app.full_name,
        'email': app.email,
        'phone': app.phone,
        'city': app.city,
        'current_role': app.current_role,
        'professional_category': app.professional_category,
        'organization': app.organization,
        'experience_level': app.experience_level,
        'skills': app.skills,
        'profile_summary': app.profile_summary,
        'interests': app.interests,
        'referral_source': app.referral_source,
        'github_url': app.github_url,
        'linkedin_url': app.linkedin_url,
        'portfolio_url': app.portfolio_url,
        'status': app.status,
        'organizer_notes': app.organizer_notes,
        'created_at': app.created_at.strftime('%b %d, %Y at %I:%M %p'),
    })

@login_required
@user_passes_test(is_organizer)
def admin_application_action(request, app_id):
    app = get_object_or_404(Application, id=app_id)
    action = request.POST.get('action')
    notes = request.POST.get('notes', '').strip()

    if action == 'APPROVE':
        app.mark_reviewed(ApplicationStatus.APPROVED, request.user, notes)

        # 1. Create or retrieve User account
        user = User.objects.filter(email=app.email).first()
        if not user:
            base_username = "".join(c for c in app.email.split('@')[0].lower() if c.isalnum() or c == '_') or "member"
            candidate_username = base_username
            counter = 1
            while User.objects.filter(username=candidate_username).exists():
                candidate_username = f"{base_username}_{counter}"
                counter += 1

            user = User.objects.create(
                email=app.email,
                username=candidate_username,
                first_name=app.full_name.split()[0] if app.full_name else '',
                last_name=" ".join(app.full_name.split()[1:]) if len(app.full_name.split()) > 1 else '',
                phone=app.phone,
                role=UserRole.MEMBER,
                is_active=True,
            )
        else:
            if user.role == UserRole.APPLICANT:
                user.role = UserRole.MEMBER
                user.save()

        # Generate secure password setup token
        token = user.generate_activation_token()

        # 2. Create or link MemberProfile
        profile, p_created = MemberProfile.objects.get_or_create(
            user=user,
            defaults={
                'application': app,
                'full_name': app.full_name,
                'professional_title': app.current_role,
                'organization': app.organization or 'Independent',
                'discipline': app.professional_category,
                'experience_level': app.experience_level,
                'location': f"{app.city}, Somaliland",
                'bio': app.profile_summary,
                'github_url': app.github_url,
                'linkedin_url': app.linkedin_url,
                'portfolio_url': app.portfolio_url,
                'profile_visibility': 'PUBLIC',
            }
        )
        if not p_created and not profile.application:
            profile.application = app
            profile.save()

        # Parse skills and link
        if app.skills:
            for s_name in [s.strip() for s in app.skills.split(',') if s.strip()]:
                skill, _ = Skill.objects.get_or_create(name=s_name)
                profile.skills.add(skill)

        # Dispatch activation email
        send_approval_notification(app, user, request)

        log_activity(
            request.user,
            'APPLICATION_APPROVED',
            f"Approved Member: {app.full_name}",
            f"Organizer {request.user.email} approved {app.full_name} ({app.current_role}).",
            request=request
        )
        notify_user(
            user,
            "Application Approved!",
            "Congratulations! Your application to TechClub has been approved. Welcome to our community.",
            "SUCCESS",
            link="/dashboard/"
        )

        activation_url = f"/accounts/activate/{token}/"
        messages.success(
            request, 
            f"Approved {app.full_name}! Member profile created. Password setup link: {activation_url}"
        )

    elif action == 'WAITLIST':
        app.mark_reviewed(ApplicationStatus.WAITLISTED, request.user, notes)
        send_status_update_notification(app, 'WAITLISTED', notes)
        log_activity(
            request.user,
            'APPLICATION_WAITLISTED',
            f"Waitlisted Application: {app.full_name}",
            f"Organizer {request.user.email} placed {app.full_name} on the waiting list.",
            request=request
        )
        messages.success(request, f"Placed {app.full_name} on Priority Waiting List successfully.")

    elif action == 'REJECT':
        app.mark_reviewed(ApplicationStatus.REJECTED, request.user, notes)
        send_status_update_notification(app, 'REJECTED', notes)
        log_activity(
            request.user,
            'APPLICATION_REJECTED',
            f"Rejected Application: {app.full_name}",
            f"Organizer {request.user.email} marked application as rejected.",
            request=request
        )
        messages.success(request, f"Application for {app.full_name} has been marked as rejected.")

    elif action == 'UPDATE_NOTES':
        app.organizer_notes = notes
        app.save()
        messages.success(request, f"Internal review notes updated for {app.full_name} successfully.")

    return redirect('admin_applications')

@login_required
@user_passes_test(is_organizer)
def admin_export_applications_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="techclub_applications_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Full Name', 'Email', 'Phone', 'City', 'Role', 'Category', 
        'Organization', 'Experience Level', 'Skills', 'Referral Source', 
        'Status', 'Organizer Notes', 'Created At'
    ])

    for app in Application.objects.all().order_by('-created_at'):
        writer.writerow([
            app.id, app.full_name, app.email, app.phone, app.city,
            app.current_role, app.professional_category, app.organization,
            app.experience_level, app.skills, app.referral_source,
            app.status, app.organizer_notes, app.created_at.strftime('%Y-%m-%d %H:%M')
        ])

    return response

@login_required
@user_passes_test(is_organizer)
def admin_notifications_log(request):
    logs = NotificationLog.objects.all().order_by('-created_at')[:50]
    return render(request, 'applications/admin_notifications.html', {'logs': logs})
