from django.urls import path
from . import views

urlpatterns = [
    path('admin-ops/meetings/', views.admin_meetings_list_view, name='admin_meetings'),
    path('admin-ops/meetings/create/', views.admin_meeting_create_view, name='admin_meeting_create'),
    path('admin-ops/meetings/<int:meeting_id>/edit/', views.admin_meeting_edit_view, name='admin_meeting_edit'),
    path('admin-ops/meetings/<int:meeting_id>/delete/', views.admin_meeting_delete_view, name='admin_meeting_delete'),
    path('admin-ops/meetings/<int:meeting_id>/action/', views.admin_meeting_action_view, name='admin_meeting_action'),
]
