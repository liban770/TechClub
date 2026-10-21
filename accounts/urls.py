from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('activate/<str:token>/', views.activate_account_view, name='activate_account'),
    path('dispatch/', views.dashboard_dispatch, name='dashboard_dispatch'),

    # Password Recovery via OTP
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),

    # Organizer User Management
    path('admin-ops/users/', views.admin_users_list_view, name='admin_users'),
    path('admin-ops/users/<int:user_id>/toggle-status/', views.admin_user_toggle_status_view, name='admin_user_toggle_status'),
    path('admin-ops/users/<int:user_id>/delete/', views.admin_user_delete_view, name='admin_user_delete'),
    path('admin-ops/users/<int:user_id>/change-role/', views.admin_user_change_role_view, name='admin_user_change_role'),
    path('admin-ops/users/<int:user_id>/reset-password/', views.admin_user_reset_password_view, name='admin_user_reset_password'),

    # In-App Notifications
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]
