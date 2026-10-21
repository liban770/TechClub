from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Announcement, AnnouncementCategory, AnnouncementAudience, PublicationStatus
from accounts.models import log_activity

def is_organizer(user):
    return user.is_authenticated and user.is_organizer

@login_required
@user_passes_test(is_organizer)
def admin_announcements_list_view(request):
    announcements = Announcement.objects.all().order_by('-is_pinned', '-created_at')

    context = {
        'announcements': announcements,
        'categories': AnnouncementCategory.choices,
        'audiences': AnnouncementAudience.choices,
        'total_count': announcements.count(),
        'published_count': announcements.filter(publication_status=PublicationStatus.PUBLISHED).count(),
    }
    return render(request, 'announcements/admin_announcements.html', context)

@login_required
@user_passes_test(is_organizer)
def admin_announcement_create_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        category = request.POST.get('category', AnnouncementCategory.NEWS)
        audience = request.POST.get('audience', AnnouncementAudience.ALL)
        is_pinned = 'is_pinned' in request.POST

        announcement = Announcement.objects.create(
            title=title,
            content=content,
            category=category,
            audience=audience,
            is_pinned=is_pinned,
            publication_status=PublicationStatus.PUBLISHED,
            created_by=request.user
        )
        log_activity(
            request.user,
            'ANNOUNCEMENT_PUBLISHED',
            f"Broadcast: {announcement.title}",
            f"Organizer published broadcast '{announcement.title}' for {announcement.audience}.",
            request=request
        )
        messages.success(request, f"Published broadcast: '{announcement.title}' successfully.")
        return redirect('admin_announcements')

    return redirect('admin_announcements')

@login_required
@user_passes_test(is_organizer)
def admin_announcement_action_view(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    action = request.POST.get('action')

    if action == 'TOGGLE_PIN':
        announcement.is_pinned = not announcement.is_pinned
        announcement.save()
        messages.info(request, f"Updated pin status for '{announcement.title}'.")
    elif action == 'ARCHIVE':
        announcement.publication_status = PublicationStatus.ARCHIVED
        announcement.save()
        messages.info(request, f"Archived announcement '{announcement.title}'.")
    elif action == 'DELETE':
        announcement.delete()
        messages.warning(request, "Announcement deleted.")

    return redirect('admin_announcements')

@login_required
@user_passes_test(is_organizer)
def admin_announcement_edit_view(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    if request.method == 'POST':
        announcement.title = request.POST.get('title', '').strip()
        announcement.content = request.POST.get('content', '').strip()
        announcement.category = request.POST.get('category', AnnouncementCategory.NEWS)
        announcement.audience = request.POST.get('audience', AnnouncementAudience.ALL)
        announcement.is_pinned = 'is_pinned' in request.POST
        announcement.save()

        log_activity(
            request.user,
            'ANNOUNCEMENT_UPDATED',
            f"Updated Broadcast: {announcement.title}",
            f"Organizer {request.user.email} updated announcement '{announcement.title}'.",
            request=request
        )
        messages.success(request, f"Announcement '{announcement.title}' updated successfully.")

    return redirect('admin_announcements')
