from django.urls import path
from . import views

urlpatterns = [
    path('apply/', views.apply_view, name='apply'),
    path('apply/success/', views.application_success_view, name='application_success'),
    path('admin-ops/applications/', views.admin_applications_list_view, name='admin_applications'),
    path('admin-ops/applications/<int:app_id>/json/', views.admin_application_detail_json, name='admin_application_json'),
    path('admin-ops/applications/<int:app_id>/action/', views.admin_application_action, name='admin_application_action'),
    path('admin-ops/applications/export/csv/', views.admin_export_applications_csv, name='admin_export_applications_csv'),
    path('admin-ops/notifications/', views.admin_notifications_log, name='admin_notifications_log'),
]
