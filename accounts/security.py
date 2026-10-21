from django.core.cache import cache

def get_client_ip(request):
    """
    Extracts the client's actual remote IP address safely.
    Uses REMOTE_ADDR by default to prevent client header spoofing.
    """
    if not request:
        return '127.0.0.1'
    # In production behind a verified reverse proxy (e.g. Nginx), X-Forwarded-For can be used.
    # Otherwise REMOTE_ADDR is untamperable by the client.
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip

def is_rate_limited(action_prefix, identifier, max_attempts=5, lockout_seconds=900):
    """
    Checks if a given action has exceeded max_attempts within lockout_seconds.
    Returns: (is_blocked: bool, remaining_lockout_seconds: int)
    """
    cache_key = f"ratelimit:{action_prefix}:{identifier}"
    record = cache.get(cache_key)
    if not record:
        return False, 0

    count = record.get('count', 0)
    if count >= max_attempts:
        return True, lockout_seconds
    return False, 0

def record_failed_action(action_prefix, identifier, max_attempts=5, lockout_seconds=900):
    """
    Increments the failure counter for the given action and identifier.
    """
    cache_key = f"ratelimit:{action_prefix}:{identifier}"
    record = cache.get(cache_key)
    if not record:
        cache.set(cache_key, {'count': 1}, timeout=lockout_seconds)
    else:
        record['count'] += 1
        cache.set(cache_key, record, timeout=lockout_seconds)

def clear_rate_limit(action_prefix, identifier):
    """
    Clears the rate limit upon successful authentication/verification.
    """
    cache_key = f"ratelimit:{action_prefix}:{identifier}"
    cache.delete(cache_key)
