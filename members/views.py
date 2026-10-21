import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from techclub_core.validators import validate_uploaded_image
from .models import MemberProfile, Skill
from applications.models import DisciplineCategory, ExperienceLevel
from accounts.models import log_activity, notify_user

def is_organizer(user):
    return user.is_authenticated and user.is_organizer

# --- PUBLIC / MEMBER DIRECTORY VIEWS ---

def member_directory_view(request):
    search_query = request.GET.get('q', '').strip()
    discipline_filter = request.GET.get('discipline', 'ALL')
    seniority_filter = request.GET.get('seniority', 'ALL')
    skill_filter = request.GET.get('skill', 'ALL')
    mentor_only = request.GET.get('mentor', '') == '1'

    members = MemberProfile.objects.exclude(profile_visibility='PRIVATE').prefetch_related('skills')

    if search_query:
        members = members.filter(
            Q(full_name__icontains=search_query) |
            Q(professional_title__icontains=search_query) |
            Q(organization__icontains=search_query) |
            Q(skills__name__icontains=search_query) |
            Q(bio__icontains=search_query)
        )

    if discipline_filter != 'ALL':
        members = members.filter(discipline=discipline_filter)

    if seniority_filter != 'ALL':
        members = members.filter(experience_level=seniority_filter)

    if skill_filter != 'ALL':
        members = members.filter(skills__name__iexact=skill_filter)

    if mentor_only:
        members = members.filter(is_mentor=True)

    members = members.distinct().order_by('-is_mentor', '-created_at')

    all_skills = Skill.objects.all().order_by('name')
    popular_skills = Skill.objects.annotate(member_count=Count('members')).filter(member_count__gt=0).order_by('-member_count')[:12]

    active_filters_count = 0
    if search_query: active_filters_count += 1
    if discipline_filter != 'ALL': active_filters_count += 1
    if seniority_filter != 'ALL': active_filters_count += 1
    if skill_filter != 'ALL': active_filters_count += 1
    if mentor_only: active_filters_count += 1

    context = {
        'members': members,
        'search_query': search_query,
        'discipline_filter': discipline_filter,
        'seniority_filter': seniority_filter,
        'skill_filter': skill_filter,
        'mentor_only': mentor_only,
        'all_skills': all_skills,
        'popular_skills': popular_skills,
        'active_filters_count': active_filters_count,
        'total_results': members.count(),
        'disciplines': DisciplineCategory.choices,
        'seniorities': ExperienceLevel.choices,
        'total_active': MemberProfile.objects.exclude(profile_visibility='PRIVATE').count(),
    }
    return render(request, 'members/directory.html', context)

def member_profile_view(request, member_id):
    member = get_object_or_404(MemberProfile, id=member_id)
    if member.profile_visibility == 'PRIVATE':
        user_is_owner = request.user.is_authenticated and request.user == member.user
        user_is_organizer = request.user.is_authenticated and getattr(request.user, 'is_organizer', False)
        if not (user_is_owner or user_is_organizer):
            raise Http404("This member profile is private.")
    return render(request, 'members/profile_detail.html', {'member': member})

@login_required
def profile_edit_view(request):
    profile, created = MemberProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': request.user.get_full_name() or request.user.username,
        }
    )

    if request.method == 'POST':
        profile.full_name = request.POST.get('full_name', '').strip()
        profile.professional_title = request.POST.get('professional_title', '').strip()
        profile.organization = request.POST.get('organization', '').strip()
        profile.discipline = request.POST.get('discipline', DisciplineCategory.SOFTWARE_ENG)
        profile.experience_level = request.POST.get('experience_level', ExperienceLevel.JUNIOR)
        profile.location = request.POST.get('location', 'Hargeisa, Somaliland').strip()
        profile.bio = request.POST.get('bio', '').strip()
        profile.avatar_url = request.POST.get('avatar_url', '').strip()
        
        # Handle file upload from computer with strict security validation
        new_photo = request.FILES.get('profile_photo')
        if new_photo:
            try:
                validate_uploaded_image(new_photo)
                profile.profile_photo = new_photo
            except ValidationError as e:
                messages.error(request, f"Security Warning: {e.message}")
                return redirect('profile_edit')

        profile.github_url = request.POST.get('github_url', '').strip()
        profile.linkedin_url = request.POST.get('linkedin_url', '').strip()
        profile.portfolio_url = request.POST.get('portfolio_url', '').strip()
        profile.profile_visibility = request.POST.get('profile_visibility', 'PUBLIC')
        profile.show_email = 'show_email' in request.POST
        profile.show_phone = 'show_phone' in request.POST

        profile.save()

        # Update skills
        skills_str = request.POST.get('skills_input', '').strip()
        if skills_str:
            profile.skills.clear()
            for s_name in [s.strip() for s in skills_str.split(',') if s.strip()]:
                skill, _ = Skill.objects.get_or_create(name=s_name)
                profile.skills.add(skill)

        log_activity(
            request.user,
            'PROFILE_UPDATED',
            "Profile Updated",
            f"{profile.full_name} updated their member profile details.",
            request=request
        )
        notify_user(
            request.user,
            "Profile Updated",
            "Your community member profile was saved successfully.",
            "SUCCESS",
            link=f"/members/{profile.id}/"
        )

        messages.success(request, "Your member profile has been updated successfully!")
        return redirect('member_profile', member_id=profile.id)

    skills_joined = ", ".join([s.name for s in profile.skills.all()])
    context = {
        'profile': profile,
        'skills_joined': skills_joined,
        'disciplines': DisciplineCategory.choices,
        'seniorities': ExperienceLevel.choices,
    }
    return render(request, 'members/profile_edit.html', context)

# --- ORGANIZER ADMIN MEMBER MANAGEMENT ---

@login_required
@user_passes_test(is_organizer)
def admin_members_list_view(request):
    search = request.GET.get('q', '').strip()
    members = MemberProfile.objects.all().order_by('-created_at')

    if search:
        members = members.filter(
            full_name__icontains=search
        ) | members.filter(
            user__email__icontains=search
        ) | members.filter(
            professional_title__icontains=search
        )

    context = {
        'members': members,
        'search': search,
    }
    return render(request, 'members/admin_members.html', context)

@login_required
@user_passes_test(is_organizer)
def admin_export_members_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="techclub_members_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Full Name', 'Email', 'Role/Title', 'Discipline', 'Organization',
        'Experience Level', 'Location', 'Is Mentor', 'Cohort', 'Created At'
    ])

    for m in MemberProfile.objects.all().order_by('-created_at'):
        writer.writerow([
            m.id, m.full_name, m.user.email, m.professional_title, m.discipline,
            m.organization, m.experience_level, m.location,
            'Yes' if m.is_mentor else 'No', m.cohort, m.created_at.strftime('%Y-%m-%d')
        ])

    return response
