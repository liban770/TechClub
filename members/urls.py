from django.urls import path
from . import views

urlpatterns = [
    path('directory/', views.member_directory_view, name='member_directory'),
    path('members/', views.member_directory_view, name='members_alias'),
    path('directory/<int:member_id>/', views.member_profile_view, name='member_profile'),
    path('member/profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('admin-ops/members/', views.admin_members_list_view, name='admin_members'),
    path('admin-ops/members/export/csv/', views.admin_export_members_csv, name='admin_export_members_csv'),
]
