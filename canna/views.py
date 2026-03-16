"""
General views for the entire project.

Contains views that don't belong to specific apps.
"""

from django.http import HttpResponse
from django.conf import settings


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
        f"Sitemap: {protocol}://{domain}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
