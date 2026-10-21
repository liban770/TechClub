from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('events/', views.public_events_view, name='public_events'),
    path('events/<int:event_id>/', views.event_detail_view, name='event_detail'),
    path('events/<int:event_id>/register/', views.event_register_action, name='event_register'),
    path('events/resources/<int:resource_id>/download/', views.event_resource_download_view, name='event_resource_download'),
    path('events/ticket/<str:ticket_code>/', views.event_ticket_view, name='event_ticket'),
    path('events/ticket/<str:ticket_code>/cancel/', views.event_ticket_cancel_view, name='event_ticket_cancel'),
    path('events/ticket/<str:ticket_code>/feedback/', views.event_submit_feedback_view, name='event_submit_feedback'),
    path('events/ticket/<str:ticket_code>/join-live/', views.event_join_live_view, name='event_join_live'),
    path('events/<int:event_id>/calendar.ics', views.event_calendar_ics_view, name='event_calendar_ics'),
    path('events/certificate/<str:certificate_id>/', views.event_certificate_view, name='event_certificate'),
    path('events/certificate/<str:certificate_id>/pdf/', views.event_certificate_pdf_view, name='event_certificate_pdf'),
    path('verify/<str:certificate_id>/', views.event_certificate_view, name='verify_certificate'),
    path('admin-ops/scan-ticket/', views.admin_ticket_scan_view, name='admin_ticket_scan'),
    path('admin-ops/events/', views.admin_events_list_view, name='admin_events'),
    path('admin-ops/events/create/', views.admin_event_create_view, name='admin_event_create'),
    path('admin-ops/events/<int:event_id>/edit/', views.admin_event_edit_view, name='admin_event_edit'),
    path('admin-ops/events/<int:event_id>/delete/', views.admin_event_delete_view, name='admin_event_delete'),
    path('admin-ops/events/<int:event_id>/resource/upload/', views.admin_event_resource_upload_view, name='admin_event_resource_upload'),
    path('admin-ops/resources/<int:resource_id>/role/', views.admin_event_resource_role_update_view, name='admin_event_resource_role_update'),
    path('admin-ops/resources/<int:resource_id>/delete/', views.admin_event_resource_delete_view, name='admin_event_resource_delete'),
    path('admin-ops/events/<int:event_id>/toggle-live/', views.admin_event_toggle_live_view, name='admin_event_toggle_live'),
    path('admin-ops/attendance/', views.admin_attendance_view, name='admin_attendance'),
    path('admin-ops/attendance/<int:event_id>/', views.admin_attendance_view, name='admin_attendance_event'),
    path('admin-ops/attendance/toggle/<int:reg_id>/', views.admin_attendance_toggle, name='admin_attendance_toggle'),
    path('admin-ops/attendance/<int:event_id>/export/csv/', views.admin_export_attendance_csv, name='admin_export_attendance_csv'),
    # Convenient alias redirects for events/admin/ paths
    path('events/admin/events/<int:event_id>/edit/', RedirectView.as_view(pattern_name='admin_event_edit', permanent=False)),
    path('events/admin/events/', RedirectView.as_view(pattern_name='admin_events', permanent=False)),
]
