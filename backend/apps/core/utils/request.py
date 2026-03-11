"""
Request Utilities
=================
Helper functions for working with HTTP requests.
"""

import re
from typing import Optional

from django.http import HttpRequest


def get_client_ip(request: HttpRequest) -> Optional[str]:
    """
    Extract client IP from request, handling proxies.

    Checks X-Forwarded-For header first (for proxied requests),
    falls back to REMOTE_ADDR.

    Args:
        request: Django HTTP request object

    Returns:
        Client IP address as string, or None if not available
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def parse_user_agent(ua_string: str) -> dict:
    """
    Parse a User-Agent string into a human-readable device name and type.

    Returns dict with 'device_name' and 'device_type'.
    Falls back to 'Unknown Browser' if parsing fails.

    Args:
        ua_string: Raw User-Agent header value

    Returns:
        Dict with 'device_name' (e.g., "Chrome on Windows") and 'device_type'
    """
    if not ua_string:
        return {'device_name': '', 'device_type': 'unknown'}

    # Detect browser
    browser = 'Unknown Browser'
    # Order matters — check specific browsers before generic ones
    browser_patterns = [
        (r'Edg[e/](\d+)', 'Edge'),
        (r'OPR/(\d+)', 'Opera'),
        (r'Brave', 'Brave'),
        (r'Vivaldi/(\d+)', 'Vivaldi'),
        (r'Chrome/(\d+)', 'Chrome'),
        (r'Firefox/(\d+)', 'Firefox'),
        (r'Safari/(\d+)', 'Safari'),
    ]
    for pattern, name in browser_patterns:
        if re.search(pattern, ua_string):
            browser = name
            break

    # Detect OS
    os_name = ''
    os_patterns = [
        (r'Windows NT 10', 'Windows'),
        (r'Windows NT', 'Windows'),
        (r'Mac OS X', 'macOS'),
        (r'iPhone|iPad', 'iOS'),
        (r'Android', 'Android'),
        (r'Linux', 'Linux'),
        (r'CrOS', 'ChromeOS'),
    ]
    for pattern, name in os_patterns:
        if re.search(pattern, ua_string):
            os_name = name
            break

    # Detect device type
    device_type = 'web'
    if re.search(r'Mobile|iPhone|Android.*Mobile', ua_string):
        device_type = 'ios' if 'iPhone' in ua_string else 'android'

    device_name = f"{browser} on {os_name}" if os_name else browser

    return {'device_name': device_name, 'device_type': device_type}
