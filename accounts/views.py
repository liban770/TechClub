from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q
from .models import User, UserRole, InAppNotification, UserActivity, log_activity, notify_user
from .security import (
    get_client_ip,
    is_rate_limited,
    record_failed_action,
    clear_rate_limit,
)
from applications.emails import send_password_reset_otp

def is_organizer(user):
    return user.is_authenticated and user.is_organizer

# --- AUTHENTICATION VIEWS ---

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_dispatch')

    if request.method == 'POST':
        login_val = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        client_ip = get_client_ip(request)
        rate_key = f"{client_ip}:{login_val.lower()}"

        # 1. Enforce Brute-Force Rate Limiting (Max 5 failed attempts per 15 minutes)
        is_blocked, _ = is_rate_limited('login', rate_key, max_attempts=5, lockout_seconds=900)
        if is_blocked:
            messages.error(request, "Too many failed login attempts. To protect your account, access is temporarily locked. Please wait 15 minutes.")
            return render(request, 'accounts/login.html')

        # Attempt login by email first, then fallback to username lookup
        user = authenticate(request, username=login_val.lower(), password=password)
        if user is None:
            matched = User.objects.filter(username__iexact=login_val).first()
            if matched:
                user = authenticate(request, username=matched.email, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "Your account has been deactivated. Please contact the TechClub organizers.")
                return render(request, 'accounts/login.html')

            # Clear failed login counter upon successful authentication
            clear_rate_limit('login', rate_key)

            login(request, user)
            log_activity(
                user,
                'LOGIN',
                'User Signed In',
                f"{user.get_full_name() or user.email} signed into the platform.",
                request=request
            )
            messages.success(request, f"Welcome back, {user.first_name or user.username}! You are signed in.")
            return redirect('dashboard_dispatch')
        else:
            record_failed_action('login', rate_key, max_attempts=5, lockout_seconds=900)
            messages.error(request, "Invalid email address or password. Please try again.")

    return render(request, 'accounts/login.html')

def logout_view(request):
    if request.user.is_authenticated:
        log_activity(
            request.user,
            'LOGOUT',
            'User Signed Out',
            f"{request.user.email} signed out.",
            request=request
        )
    logout(request)
    messages.success(request, "You have been signed out safely. See you soon!")
    return redirect('home')

def activate_account_view(request, token):
    user = get_object_or_404(User, activation_token=token)

    # 1. Enforce Token Expiration (72 hours max)
    if not user.is_activation_token_valid():
        messages.error(request, "This activation link has expired (activation links are valid for 72 hours). Please contact TechClub organizers for a new link.")
        return redirect('login')

    if request.method == 'POST':
        new_password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'accounts/activate.html', {'target_user': user, 'token': token})

        # 2. Strict Password Complexity Validation
        try:
            validate_password(new_password, user=user)
        except ValidationError as err:
            for error_msg in err.messages:
                messages.error(request, error_msg)
            return render(request, 'accounts/activate.html', {'target_user': user, 'token': token})

        user.set_password(new_password)
        user.activation_token = None
        user.activation_token_created_at = None
        user.must_set_password = False
        user.is_active = True
        user.save()

        log_activity(
            user,
            'ACCOUNT_ACTIVATED',
            'Account Password Set & Activated',
            f"Account for {user.email} was activated via setup token.",
            request=request
        )
        notify_user(
            user,
            "Welcome to TechClub!",
            "Your account is fully activated. Explore upcoming meetups, connect in the directory, and build together.",
            "SUCCESS",
            link="/dashboard/"
        )

        login(request, user)
        messages.success(request, "Your password has been set and your account is active! Welcome to TechClub.")
        return redirect('member_dashboard')

    return render(request, 'accounts/activate.html', {'target_user': user, 'token': token})

def dashboard_dispatch(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_organizer:
        return redirect('admin_overview')
    return redirect('member_dashboard')

# --- PASSWORD RECOVERY WITH EMAIL OTP ---

def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_dispatch')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        client_ip = get_client_ip(request)
        rate_key = f"{client_ip}:{email}"

        # Enforce rate limit (Max 3 OTP requests per 15 mins to prevent email bombing)
        is_blocked, _ = is_rate_limited('forgot_pwd', rate_key, max_attempts=3, lockout_seconds=900)
        if is_blocked:
            messages.error(request, "Too many password reset requests. Please check your inbox or wait 15 minutes before requesting again.")
            return render(request, 'accounts/forgot_password.html', {'email': email})

        record_failed_action('forgot_pwd', rate_key, max_attempts=3, lockout_seconds=900)

        user = User.objects.filter(email__iexact=email).first()

        if user:
            otp_code = user.generate_otp()
            send_password_reset_otp(user, otp_code, request=request)
            
            log_activity(
                user,
                'PASSWORD_RESET_REQUESTED',
                'Password Reset OTP Dispatched',
                f"6-digit OTP code requested for {user.email}.",
                request=request
            )
            notify_user(
                user,
                "Password Reset Requested",
                "A password reset code was requested for your account.",
                "SECURITY"
            )

            messages.success(request, f"A 6-digit verification code has been dispatched to {email}. Enter it below.")
            return redirect(f"/accounts/verify-otp/?email={email}")
        else:
            messages.error(request, f"No registered account found with email '{email}'. Please check your spelling or apply to join.")
            return render(request, 'accounts/forgot_password.html', {'email': email})

    return render(request, 'accounts/forgot_password.html')

def verify_otp_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_dispatch')

    email = request.GET.get('email', '') or request.POST.get('email', '')
    email = email.strip().lower()

    target_user = User.objects.filter(email__iexact=email).first() if email else None

    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not target_user:
            messages.error(request, "Invalid or missing account email. Please restart recovery.")
            return redirect('forgot_password')

        # Verify OTP (auto-burns after 5 failed guesses)
        if not target_user.verify_otp(otp_code):
            messages.error(request, "Invalid or expired verification OTP. (Max 5 attempts allowed before code is invalidated).")
            return render(request, 'accounts/verify_otp.html', {'email': email})

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'accounts/verify_otp.html', {'email': email})

        # Validate password complexity
        try:
            validate_password(new_password, user=target_user)
        except ValidationError as err:
            for error_msg in err.messages:
                messages.error(request, error_msg)
            return render(request, 'accounts/verify_otp.html', {'email': email})

        # Reset password successfully
        target_user.set_password(new_password)
        target_user.clear_otp()
        target_user.must_set_password = False
        target_user.is_active = True
        target_user.save()

        log_activity(
            target_user,
            'PASSWORD_RESET_SUCCESS',
            'Password Successfully Reset via OTP',
            f"Password for {target_user.email} was successfully reset using 6-digit email OTP.",
            request=request
        )

        notify_user(
            target_user,
            "Password Changed",
            "Your account password was successfully reset using OTP verification.",
            "SECURITY"
        )

        login(request, target_user)
        messages.success(request, "Password reset successfully! You are now securely signed in to TechClub.")
        return redirect('dashboard_dispatch')

    return render(request, 'accounts/verify_otp.html', {
        'email': email,
    })

def resend_otp_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        if user:
            otp_code = user.generate_otp()
            send_password_reset_otp(user, otp_code, request=request)
            messages.success(request, f"New verification code dispatched to {email}!")
            return redirect(f"/accounts/verify-otp/?email={email}")
        else:
            messages.error(request, "Account not found.")
            return redirect('forgot_password')

    return redirect('forgot_password')

# --- ORGANIZER USER MANAGEMENT ---

@login_required
@user_passes_test(is_organizer)
def admin_users_list_view(request):
    search_query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', 'ALL')
    status_filter = request.GET.get('status', 'ALL')

    users_qs = User.objects.all().order_by('-date_joined')

    if search_query:
        users_qs = users_qs.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    if role_filter != 'ALL':
        users_qs = users_qs.filter(role=role_filter)

    if status_filter == 'ACTIVE':
        users_qs = users_qs.filter(is_active=True)
    elif status_filter == 'INACTIVE':
        users_qs = users_qs.filter(is_active=False)

    total_users = User.objects.count()
    organizers_count = User.objects.filter(Q(role=UserRole.ORGANIZER) | Q(is_superuser=True)).distinct().count()
    members_count = User.objects.filter(role=UserRole.MEMBER).count()
    active_count = User.objects.filter(is_active=True).count()
    inactive_count = User.objects.filter(is_active=False).count()

    context = {
        'users': users_qs,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'total_users': total_users,
        'organizers_count': organizers_count,
        'members_count': members_count,
        'active_count': active_count,
        'inactive_count': inactive_count,
    }
    return render(request, 'accounts/admin_users.html', context)

@login_required
@user_passes_test(is_organizer)
def admin_user_toggle_status_view(request, user_id):
    if request.method == 'POST':
        target = get_object_or_404(User, id=user_id)
        if target.id == request.user.id:
            messages.error(request, "You cannot deactivate your own account!")
            return redirect('admin_users')

        target.is_active = not target.is_active
        target.save()

        action_label = "activated" if target.is_active else "deactivated"
        log_activity(
            request.user,
            'USER_STATUS_TOGGLED',
            f"User {target.email} {action_label.capitalize()}",
            f"Organizer {request.user.email} changed {target.email} status to {action_label}.",
            request=request
        )
        notify_user(
            target,
            f"Account Status Update: {action_label.capitalize()}",
            f"Your TechClub account has been {action_label} by an administrator.",
            "WARNING" if not target.is_active else "SUCCESS"
        )
        messages.success(request, f"User {target.email} has been successfully {action_label}.")

    return redirect('admin_users')

@login_required
@user_passes_test(is_organizer)
def admin_user_delete_view(request, user_id):
    if request.method == 'POST':
        target = get_object_or_404(User, id=user_id)
        if target.id == request.user.id:
            messages.error(request, "You cannot delete your own account!")
            return redirect('admin_users')

        if target.is_superuser and not request.user.is_superuser:
            messages.error(request, "Only a superuser can delete another administrator/superuser account!")
            return redirect('admin_users')

        target_email = target.email
        target_name = target.get_full_name() or target.username

        log_activity(
            request.user,
            'USER_DELETED',
            f"User Deleted: {target_email}",
            f"Organizer {request.user.email} permanently deleted user account {target_email} ({target_name}).",
            request=request
        )

        target.delete()
        messages.success(request, f"User account '{target_email}' has been permanently deleted.")

    return redirect('admin_users')

@login_required
@user_passes_test(is_organizer)
def admin_user_change_role_view(request, user_id):
    if request.method == 'POST':
        target = get_object_or_404(User, id=user_id)
        new_role = request.POST.get('new_role')

        if new_role in [UserRole.ORGANIZER, UserRole.MEMBER, UserRole.APPLICANT]:
            target.role = new_role
            if new_role == UserRole.ORGANIZER:
                target.is_staff = True
            elif not target.is_superuser:
                target.is_staff = False
            target.save()

            log_activity(
                request.user,
                'USER_ROLE_CHANGED',
                f"Role changed for {target.email}",
                f"Organizer {request.user.email} changed role of {target.email} to {target.get_role_display()}.",
                request=request
            )
            notify_user(
                target,
                "Role Updated",
                f"Your account role has been updated to {target.get_role_display()}.",
                "INFO"
            )
            messages.success(request, f"Updated role for {target.email} to {target.get_role_display()} successfully.")

    return redirect('admin_users')

@login_required
@user_passes_test(is_organizer)
def admin_user_reset_password_view(request, user_id):
    if request.method == 'POST':
        target = get_object_or_404(User, id=user_id)
        new_password = request.POST.get('new_password', '').strip()

        if len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return redirect('admin_users')

        target.set_password(new_password)
        target.save()

        log_activity(
            request.user,
            'ADMIN_PASSWORD_RESET',
            f"Admin reset password for {target.email}",
            f"Organizer {request.user.email} reset password for {target.email}.",
            request=request
        )
        notify_user(
            target,
            "Security Notice: Password Reset",
            "An administrator has set a temporary password for your account.",
            "SECURITY"
        )
        messages.success(request, f"Password successfully updated for {target.email}.")

    return redirect('admin_users')

# --- IN-APP NOTIFICATIONS API & ACTIONS ---

@login_required
def mark_notification_read(request, pk):
    notif = get_object_or_404(InAppNotification, id=pk, recipient=request.user)
    notif.is_read = True
    notif.save()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    messages.success(request, "Notification marked as read.")
    if notif.link:
        return redirect(notif.link)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard_dispatch'))

@login_required
def mark_all_notifications_read(request):
    InAppNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    messages.success(request, "All notifications marked as read.")
    return redirect(request.META.get('HTTP_REFERER', 'dashboard_dispatch'))
