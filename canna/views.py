"""
General views for the entire project.

Contains views that don't belong to specific apps.
"""

from django.http import HttpResponse


def robots_txt(request):
    """
    Serve robots.txt dynamically.

    Returns:
        - User-agent: * (allow all bots)
        - Allow: / (allow all pages)
        - Sitemap: link to sitemap.xml

    This helps search engines find and index the site correctly.
    """
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
