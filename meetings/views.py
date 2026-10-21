from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Meeting, MeetingParticipant, MeetingPurpose, MeetingStatus
from members.models import MemberProfile
from django.core.exceptions import ValidationError
from techclub_core.validators import validate_uploaded_image
from accounts.models import log_activity, notify_user

def is_organizer(user):
    return user.is_authenticated and user.is_organizer

@login_required
@user_passes_test(is_organizer)
def admin_meetings_list_view(request):
    status_filter = request.GET.get('status', 'ALL')
    meetings = Meeting.objects.all().order_by('-start_datetime')

    if status_filter != 'ALL':
        meetings = meetings.filter(status=status_filter)

    total_sessions = Meeting.objects.count()
    confirmed_sessions = Meeting.objects.filter(status=MeetingStatus.CONFIRMED).count()
    completed_sessions = Meeting.objects.filter(status=MeetingStatus.COMPLETED).count()
    mentors_count = MemberProfile.objects.filter(is_mentor=True).count()

    all_members = MemberProfile.objects.all().order_by('full_name')

    context = {
        'meetings': meetings,
        'status_filter': status_filter,
        'total_sessions': total_sessions,
        'confirmed_sessions': confirmed_sessions,
        'completed_sessions': completed_sessions,
        'mentors_count': mentors_count,
        'purposes': MeetingPurpose.choices,
        'all_members': all_members,
    }
    return render(request, 'meetings/admin_meetings.html', context)

@login_required
@user_passes_test(is_organizer)
def admin_meeting_create_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        purpose = request.POST.get('purpose', MeetingPurpose.MENTORSHIP)
        start_datetime = request.POST.get('start_datetime')
        end_datetime = request.POST.get('end_datetime')
        venue = request.POST.get('venue', 'Hargeisa, Somaliland').strip()
        meeting_link = request.POST.get('meeting_link', '').strip()
        mentor_id = request.POST.get('mentor_id')
        mentee_id = request.POST.get('mentee_id')
        notes = request.POST.get('notes', '').strip()

        cover_image = request.FILES.get('cover_image')
        if cover_image:
            try:
                validate_uploaded_image(cover_image)
            except ValidationError as e:
                messages.error(request, f"Security Warning: {e.message}")
                return redirect('admin_meetings')

        if mentor_id and mentee_id and mentor_id == mentee_id:
            messages.error(request, "Mentor and Mentee cannot be the same member.")
            return redirect('admin_meetings')

        meeting = Meeting.objects.create(
            title=title,
            purpose=purpose,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            venue=venue,
            meeting_link=meeting_link,
            cover_image=cover_image if cover_image else None,
            organizer_notes=notes,
            status=MeetingStatus.CONFIRMED,
            created_by=request.user
        )

        if mentor_id:
            mentor = MemberProfile.objects.filter(id=mentor_id).first()
            if mentor:
                if mentor.user and not mentor.user.is_active:
                    messages.warning(request, f"Note: Mentor {mentor.full_name}'s account is currently deactivated.")
                MeetingParticipant.objects.update_or_create(
                    meeting=meeting, member=mentor,
                    defaults={'role_in_meeting': 'MENTOR', 'status': 'ACCEPTED'}
                )
                if mentor.user and mentor.user.is_active:
                    notify_user(
                        mentor.user,
                        f"Mentorship Session: {meeting.title}",
                        f"You are confirmed as Mentor for '{meeting.title}' at {meeting.venue}.",
                        "MEETING"
                    )

        if mentee_id:
            mentee = MemberProfile.objects.filter(id=mentee_id).first()
            if mentee:
                if mentee.user and not mentee.user.is_active:
                    messages.warning(request, f"Note: Mentee {mentee.full_name}'s account is currently deactivated.")
                MeetingParticipant.objects.update_or_create(
                    meeting=meeting, member=mentee,
                    defaults={'role_in_meeting': 'MENTEE', 'status': 'ACCEPTED'}
                )
                if mentee.user and mentee.user.is_active:
                    notify_user(
                        mentee.user,
                        f"Mentorship Session: {meeting.title}",
                        f"Your session '{meeting.title}' with {mentor.full_name if mentor_id and mentor else 'Mentor'} has been scheduled.",
                        "MEETING"
                    )

        log_activity(
            request.user,
            'MEETING_SCHEDULED',
            f"Scheduled Meeting: {meeting.title}",
            f"Organizer scheduled session '{meeting.title}'.",
            request=request
        )

        messages.success(request, f"Scheduled meeting: '{meeting.title}' successfully.")
        return redirect('admin_meetings')

    return redirect('admin_meetings')

@login_required
@user_passes_test(is_organizer)
def admin_meeting_edit_view(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)
    all_members = MemberProfile.objects.all().order_by('full_name')

    mentor_part = meeting.participants.filter(role_in_meeting='MENTOR').first()
    mentee_part = meeting.participants.filter(role_in_meeting='MENTEE').first()

    if request.method == 'POST':
        meeting.title = request.POST.get('title', '').strip()
        meeting.purpose = request.POST.get('purpose', MeetingPurpose.MENTORSHIP)
        meeting.start_datetime = request.POST.get('start_datetime')
        meeting.end_datetime = request.POST.get('end_datetime')
        meeting.venue = request.POST.get('venue', 'Hargeisa, Somaliland').strip()
        meeting.meeting_link = request.POST.get('meeting_link', '').strip()
        meeting.organizer_notes = request.POST.get('notes', '').strip()
        meeting.status = request.POST.get('status', MeetingStatus.CONFIRMED)

        # Upload cover image from computer with strict security validation
        new_cover = request.FILES.get('cover_image')
        if new_cover:
            try:
                validate_uploaded_image(new_cover)
                meeting.cover_image = new_cover
            except ValidationError as e:
                messages.error(request, f"Security Warning: {e.message}")
                return redirect('admin_meeting_edit', meeting_id=meeting.id)

        meeting.save()

        # Update Mentor
        new_mentor_id = request.POST.get('mentor_id')
        if new_mentor_id:
            mentor = MemberProfile.objects.filter(id=new_mentor_id).first()
            if mentor:
                MeetingParticipant.objects.update_or_create(
                    meeting=meeting,
                    role_in_meeting='MENTOR',
                    defaults={'member': mentor, 'status': 'ACCEPTED'}
                )
        elif mentor_part:
            mentor_part.delete()

        # Update Mentee
        new_mentee_id = request.POST.get('mentee_id')
        if new_mentee_id:
            mentee = MemberProfile.objects.filter(id=new_mentee_id).first()
            if mentee:
                MeetingParticipant.objects.update_or_create(
                    meeting=meeting,
                    role_in_meeting='MENTEE',
                    defaults={'member': mentee, 'status': 'ACCEPTED'}
                )
        elif mentee_part:
            mentee_part.delete()

        log_activity(
            request.user,
            'MEETING_UPDATED',
            f"Updated Meeting: {meeting.title}",
            f"Organizer {request.user.email} updated meeting session '{meeting.title}'.",
            request=request
        )
        messages.success(request, f"Meeting '{meeting.title}' updated successfully.")
        return redirect('admin_meetings')

    context = {
        'meeting': meeting,
        'purposes': MeetingPurpose.choices,
        'statuses': MeetingStatus.choices,
        'all_members': all_members,
        'current_mentor_id': mentor_part.member.id if mentor_part else None,
        'current_mentee_id': mentee_part.member.id if mentee_part else None,
    }
    return render(request, 'meetings/admin_meeting_edit.html', context)

@login_required
@user_passes_test(is_organizer)
def admin_meeting_delete_view(request, meeting_id):
    if request.method == 'POST':
        meeting = get_object_or_404(Meeting, id=meeting_id)
        title = meeting.title
        log_activity(
            request.user,
            'MEETING_DELETED',
            f"Deleted Meeting: {title}",
            f"Organizer {request.user.email} permanently removed meeting '{title}'.",
            request=request
        )
        meeting.delete()
        messages.success(request, f"Meeting session '{title}' deleted successfully.")
    return redirect('admin_meetings')

@login_required
@user_passes_test(is_organizer)
def admin_meeting_action_view(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)
    action = request.POST.get('action')

    if action == 'COMPLETE':
        meeting.status = MeetingStatus.COMPLETED
        meeting.save()
        messages.success(request, f"Marked '{meeting.title}' as Completed.")
    elif action == 'CANCEL':
        meeting.status = MeetingStatus.CANCELLED
        meeting.save()
        messages.warning(request, f"Cancelled session '{meeting.title}'.")

    return redirect('admin_meetings')
