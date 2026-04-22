import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


SOURCE_FILES = [
    "fonts.css",
    "styles_v2.css",
    "auth.css",
    "cookie-consent.css",
    "registration-banner.css",
]
BUNDLE_NAME = "bundle_v2.css"
CHARSET_RE = re.compile(r'^\s*@charset\s+"[^"]+";\s*', re.IGNORECASE)


class Command(BaseCommand):
    help = "Concatenate common CSS files into a single bundle for fewer render-blocking requests."

    def handle(self, *args, **options):
        css_dir = Path(settings.BASE_DIR) / "static" / "css"
        if not css_dir.is_dir():
            raise CommandError(f"CSS directory not found: {css_dir}")

        parts = [
            '@charset "utf-8";',
            "/* ==== bundle_v2.css ==== */",
            "/* Built by: python manage.py build_css_bundle (do not edit directly) */",
        ]

        for name in SOURCE_FILES:
            source = css_dir / name
            if not source.exists():
                raise CommandError(f"Missing source CSS: {source}")
            content = CHARSET_RE.sub("", source.read_text(encoding="utf-8"))
            parts.append(f"\n/* === {name} === */")
            parts.append(content)

        bundle_path = css_dir / BUNDLE_NAME
        bundle_path.write_text("\n".join(parts), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(
            f"Wrote {bundle_path} ({bundle_path.stat().st_size} bytes, "
            f"{len(SOURCE_FILES)} source files)"
        ))
