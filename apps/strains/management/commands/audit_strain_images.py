"""Audit Strain hero images on S3: size, content-type, format mismatches.

Read-only. Does not write to S3 or DB. Intended as the inspection step before
running `compress_strain_images`.
"""

import csv
from io import StringIO
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.strains.models import Strain


LARGE_KB = 400
MEDIUM_KB = 150

CONTENT_TYPE_BY_EXT = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
}


def _s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def _media_key(name: str) -> str:
    return f"{settings.PUBLIC_MEDIA_LOCATION}/{name}"


class Command(BaseCommand):
    help = "Audit Strain hero images on S3 (size, content-type, format mismatches)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Only audit first N strains.")
        parser.add_argument("--output", type=str, default=None, help="Write CSV to file.")
        parser.add_argument(
            "--include-orphans",
            action="store_true",
            help="Also list S3 objects under media/strains/images/ not referenced by any Strain.",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "AWS_STORAGE_BUCKET_NAME", None):
            raise CommandError("AWS_STORAGE_BUCKET_NAME not set; enable USE_S3.")

        bucket = settings.AWS_STORAGE_BUCKET_NAME
        s3 = _s3_client()

        qs = Strain.objects.exclude(img="").exclude(img__isnull=True).order_by("slug")
        if options["limit"]:
            qs = qs[: options["limit"]]

        total = qs.count()
        self.stdout.write(f"Auditing {total} strains with images on bucket '{bucket}'...")

        rows = []
        referenced_keys = set()

        count_by_category = {"ok": 0, "medium": 0, "large": 0, "error": 0}
        count_mismatch = 0
        size_total = 0
        size_large = 0
        size_by_format = {}

        for i, strain in enumerate(qs.iterator(), start=1):
            name = strain.img.name
            key = _media_key(name)
            referenced_keys.add(key)
            ext = Path(name).suffix.lower().lstrip(".")
            row = {
                "slug": strain.slug,
                "key": key,
                "ext": ext,
                "size_kb": "",
                "content_type": "",
                "category": "",
                "mismatch": "",
                "error": "",
            }

            try:
                head = s3.head_object(Bucket=bucket, Key=key)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "unknown")
                row["error"] = code
                row["category"] = "error"
                count_by_category["error"] += 1
                rows.append(row)
                continue

            size = head["ContentLength"]
            ct = head.get("ContentType", "")
            size_total += size
            size_by_format[ext] = size_by_format.get(ext, 0) + size

            row["size_kb"] = size // 1024
            row["content_type"] = ct

            expected_ct = CONTENT_TYPE_BY_EXT.get(ext)
            mismatch = bool(expected_ct and expected_ct != ct)
            row["mismatch"] = "yes" if mismatch else ""
            if mismatch:
                count_mismatch += 1

            if size >= LARGE_KB * 1024:
                row["category"] = "large"
                count_by_category["large"] += 1
                size_large += size
            elif size >= MEDIUM_KB * 1024:
                row["category"] = "medium"
                count_by_category["medium"] += 1
            else:
                row["category"] = "ok"
                count_by_category["ok"] += 1

            rows.append(row)

            if i % 50 == 0:
                self.stdout.write(f"  ...scanned {i}/{total}")

        buf = StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["slug", "key", "ext", "content_type", "size_kb", "category", "mismatch", "error"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        csv_text = buf.getvalue()

        if options["output"]:
            path = Path(options["output"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(csv_text, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Wrote CSV to {path}"))
        else:
            self.stdout.write("\n=== CSV ===")
            self.stdout.write(csv_text)

        self.stdout.write("\n=== Summary ===")
        self.stdout.write(f"Total strains with img: {len(rows)}")
        self.stdout.write(f"Total size: {size_total // 1024} KB ({size_total / 1024 / 1024:.1f} MB)")
        self.stdout.write(
            f"Categories: ok={count_by_category['ok']}, "
            f"medium (>= {MEDIUM_KB} KB)={count_by_category['medium']}, "
            f"large (>= {LARGE_KB} KB)={count_by_category['large']}, "
            f"errors={count_by_category['error']}"
        )
        self.stdout.write(
            f"Large files total size: {size_large // 1024} KB "
            f"({size_large / size_total * 100:.0f}% of all if total > 0)"
            if size_total
            else ""
        )
        self.stdout.write(f"Ext/Content-Type mismatches: {count_mismatch}")
        if size_by_format:
            self.stdout.write("By extension:")
            for ext, total_size in sorted(size_by_format.items(), key=lambda kv: -kv[1]):
                self.stdout.write(f"  .{ext}: {total_size // 1024} KB")

        if options["include_orphans"]:
            self._report_orphans(s3, bucket, referenced_keys)

    def _report_orphans(self, s3, bucket, referenced_keys):
        prefix = f"{settings.PUBLIC_MEDIA_LOCATION}/strains/images/"
        self.stdout.write(f"\n=== Orphans under {prefix} ===")
        paginator = s3.get_paginator("list_objects_v2")
        orphans = []
        total_objects = 0
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                total_objects += 1
                if obj["Key"] not in referenced_keys:
                    orphans.append(obj)

        if not orphans:
            self.stdout.write(f"No orphans. ({total_objects} objects under prefix, all referenced.)")
            return

        orphans.sort(key=lambda o: -o["Size"])
        orphan_size = sum(o["Size"] for o in orphans)
        self.stdout.write(
            f"Found {len(orphans)}/{total_objects} orphan objects, total {orphan_size // 1024} KB"
        )
        for obj in orphans[:50]:
            self.stdout.write(f"  {obj['Key']}  {obj['Size'] // 1024} KB  {obj['LastModified']}")
        if len(orphans) > 50:
            self.stdout.write(f"  ... and {len(orphans) - 50} more (not shown)")
