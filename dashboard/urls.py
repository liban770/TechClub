from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('founder/', views.founder_view, name='founder'),
    path('code-of-conduct/', views.code_of_conduct_view, name='code_of_conduct'),
    path('admin-ops/', views.admin_overview_view, name='admin_overview'),
    path('admin-ops/inquiries/<int:inquiry_id>/toggle/', views.admin_inquiry_toggle_view, name='admin_inquiry_toggle'),
    path('admin-ops/founder-settings/', views.admin_founder_manage_view, name='admin_founder_manage'),
    path('admin-ops/reports/', views.admin_reports_view, name='admin_reports'),
    path('admin-ops/backup/download/', views.admin_backup_download_view, name='admin_backup_download'),
    path('partners/', views.partners_list_view, name='partners'),
    path('partners/apply/', views.partner_apply_view, name='partner_apply'),
    path('admin-ops/partners/', views.admin_partners_manage_view, name='admin_partners'),
    path('admin-ops/partners/<int:partner_id>/status/<str:new_status>/', views.admin_partner_status_view, name='admin_partner_status'),
    path('admin-ops/partners/<int:partner_id>/edit/', views.admin_partner_edit_view, name='admin_partner_edit'),
    path('admin-ops/partners/<int:partner_id>/delete/', views.admin_partner_delete_view, name='admin_partner_delete'),
    path('member/dashboard/', views.member_dashboard_view, name='member_dashboard'),
]
