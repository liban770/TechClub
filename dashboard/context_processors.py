from applications.models import Application, ApplicationStatus
from members.models import MemberProfile
from events.models import Event
from accounts.models import InAppNotification

def global_stats(request):
    try:
        pending_apps_count = Application.objects.filter(status=ApplicationStatus.PENDING).count()
        total_members_count = MemberProfile.objects.count()
        upcoming_events_count = Event.objects.filter(status='OPEN').count()
    except Exception:
        pending_apps_count = 0
        total_members_count = 0
        upcoming_events_count = 0

    unread_notifications_count = 0
    recent_notifications = []

    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            unread_notifications_count = InAppNotification.objects.filter(recipient=request.user, is_read=False).count()
            recent_notifications = InAppNotification.objects.filter(recipient=request.user).order_by('-created_at')[:6]
        except Exception:
            unread_notifications_count = 0
            recent_notifications = []

    return {
        'pending_apps_count': pending_apps_count,
        'total_members_count': total_members_count,
        'upcoming_events_count': upcoming_events_count,
        'unread_notifications_count': unread_notifications_count,
        'recent_notifications': recent_notifications,
    }

