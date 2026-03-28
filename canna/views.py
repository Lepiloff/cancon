"""
General views for the entire project.

Contains views that don't belong to specific apps.
"""

import json

from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


def robots_txt(request):
    """
    Serve robots.txt dynamically.

    Returns:
        - User-agent: * (allow all bots)
        - Allow: / (allow all pages)
        - Sitemap: link to sitemap.xml

    This helps search engines find and index the site correctly.
    """
    protocol = getattr(settings, 'SITE_PROTOCOL', 'https')
    domain = getattr(settings, 'SITE_DOMAIN', 'cannamente.com')

    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        "Disallow: /accounts/",
        "Disallow: /en/accounts/",
        "",
        f"Sitemap: {protocol}://{domain}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


COOKIE_CONSENT_MAX_AGE = 15552000  # 6 months


@csrf_exempt
@require_POST
def cookie_consent_view(request):
    """
    Accept cookie consent preferences via POST.

    Expects JSON body: {"analytics": true/false}
    Sets a cookie and saves to user profile if authenticated.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    consent = {
        "necessary": True,  # Always required
        "analytics": bool(data.get("analytics", False)),
    }

    # Save to user profile if authenticated
    if request.user.is_authenticated:
        request.user.cookie_consent = consent
        request.user.cookie_consent_date = timezone.now()
        request.user.save(update_fields=["cookie_consent", "cookie_consent_date"])

    response = JsonResponse({"status": "ok", "consent": consent})
    response.set_cookie(
        "cookie_consent",
        json.dumps(consent),
        max_age=COOKIE_CONSENT_MAX_AGE,
        samesite="Lax",
        path="/",
        httponly=False,  # JS needs to read this to conditionally load GA4
    )
    return response
