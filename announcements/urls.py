from django.urls import path
from . import views

urlpatterns = [
    path('admin-ops/announcements/', views.admin_announcements_list_view, name='admin_announcements'),
    path('admin-ops/announcements/create/', views.admin_announcement_create_view, name='admin_announcement_create'),
    path('admin-ops/announcements/<int:announcement_id>/action/', views.admin_announcement_action_view, name='admin_announcement_action'),
    path('admin-ops/announcements/<int:announcement_id>/edit/', views.admin_announcement_edit_view, name='admin_announcement_edit'),
]
