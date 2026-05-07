"""Re-encode Strain hero images on S3 in-place to reduce file size.

Two modes:

1. Default (re-encode mode):
   - Iterates S3 objects under the `media/strains/images/` prefix directly, so
     it works regardless of the local DB (prod vs staging vs local dev may
     differ).
   - Re-encodes each file in its current actual format (detected by Pillow,
     not by extension): WebP -> WebP q=80, JPEG -> JPEG q=85 progressive,
     PNG -> optimised PNG (palette when safe). The S3 key name is preserved;
     no DB update needed.
   - Skips files below --min-kb (default 200) and files that would not shrink.
   - Writes back with Cache-Control "public, max-age=31536000, immutable" so
     browsers/CDN cache the new version for a long time.

2. --cache-control-only:
   - Does not re-encode; only rewrites object metadata via S3 CopyObject with
     MetadataDirective=REPLACE. Used to retroactively apply long-cache headers
     to files that were uploaded before compress_strain_images was introduced
     (i.e. files with empty or short Cache-Control). Defaults to --min-kb 0.
   - Idempotent: HEADs each object first and skips if Cache-Control already
     matches the target. Pass --force to rewrite anyway.

Bucket versioning + lifecycle policy (14-day noncurrent retention) give a
14-day rollback window for both modes.

Run with `--dry-run` first. Add `--slug foo` or `--key foo.webp` to test a
single file. Pass `--prefix media/articles/images/` to target other folders.
"""

import io
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image


STRAIN_IMAGES_PREFIX = "media/strains/images/"
LONG_CACHE = "public, max-age=31536000, immutable"

WEBP_QUALITY = 80
JPEG_QUALITY = 85

SUPPORTED_FORMATS = {"WEBP", "JPEG", "PNG"}
EXT_BY_CONTENT_TYPE = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}


def _s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def _reencode(original_bytes: bytes) -> tuple[bytes, str, str]:
    """Decode and re-encode image in its native format.

    Returns (new_bytes, content_type, format_lowercase).
    Raises ValueError for unsupported formats.
    """
    img = Image.open(io.BytesIO(original_bytes))
    img.load()
    fmt = (img.format or "").upper()

    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"unsupported format: {fmt!r}")

    out = io.BytesIO()

    if fmt == "WEBP":
        save_kwargs = {"format": "WEBP", "quality": WEBP_QUALITY, "method": 6}
        if img.mode == "P":
            img = img.convert("RGBA")
        img.save(out, **save_kwargs)
        return out.getvalue(), "image/webp", "webp"

    if fmt == "JPEG":
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(
            out,
            format="JPEG",
            quality=JPEG_QUALITY,
            optimize=True,
            progressive=True,
        )
        return out.getvalue(), "image/jpeg", "jpeg"

    # PNG
    candidates = []
    buf_direct = io.BytesIO()
    img.save(buf_direct, format="PNG", optimize=True)
    candidates.append(buf_direct.getvalue())
    if img.mode in ("RGB", "RGBA"):
        try:
            palette_img = img.convert("P", palette=Image.ADAPTIVE, colors=256)
            buf_palette = io.BytesIO()
            palette_img.save(buf_palette, format="PNG", optimize=True)
            candidates.append(buf_palette.getvalue())
        except Exception:
            pass
    best = min(candidates, key=len)
    return best, "image/png", "png"


class Command(BaseCommand):
    help = "Re-encode Strain hero images on S3 in-place (same format, smaller size)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing to S3.",
        )
        parser.add_argument(
            "--min-kb",
            type=int,
            default=None,
            help=(
                "Only touch files of at least this size (KB). Default 200 in "
                "re-encode mode, 0 in --cache-control-only mode."
            ),
        )
        parser.add_argument(
            "--cache-control-only",
            action="store_true",
            help=(
                "Skip re-encoding; only rewrite Cache-Control metadata to "
                f"'{LONG_CACHE}' via S3 CopyObject. Idempotent."
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "With --cache-control-only, also rewrite objects whose "
                "Cache-Control already matches the target."
            ),
        )
        parser.add_argument(
            "--key",
            type=str,
            default=None,
            help="Process exactly one S3 key (e.g. media/strains/images/Rainbow.webp).",
        )
        parser.add_argument(
            "--slug",
            type=str,
            default=None,
            help="Process only the hero image of the given Strain slug (requires DB access).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop after processing N candidates (useful for test batches).",
        )
        parser.add_argument(
            "--prefix",
            type=str,
            default=STRAIN_IMAGES_PREFIX,
            help=f"S3 prefix to scan. Default {STRAIN_IMAGES_PREFIX}",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "AWS_STORAGE_BUCKET_NAME", None):
            raise CommandError("AWS_STORAGE_BUCKET_NAME not set; enable USE_S3.")

        if options["force"] and not options["cache_control_only"]:
            raise CommandError("--force only applies with --cache-control-only.")

        cache_only = options["cache_control_only"]
        if options["min_kb"] is None:
            options["min_kb"] = 0 if cache_only else 200

        bucket = settings.AWS_STORAGE_BUCKET_NAME
        s3 = _s3_client()
        dry = options["dry_run"]
        min_bytes = options["min_kb"] * 1024
        limit = options["limit"]

        candidates = self._collect_candidates(s3, bucket, options)

        # Filter by size
        before_count = len(candidates)
        candidates = [c for c in candidates if c["size"] >= min_bytes]
        below_threshold = before_count - len(candidates)

        mode_label = (
            "CACHE-CONTROL-ONLY (DRY-RUN)" if cache_only and dry
            else "CACHE-CONTROL-ONLY" if cache_only
            else "DRY-RUN" if dry
            else "WRITE"
        )
        self.stdout.write(
            f"Mode: {mode_label}  |  "
            f"prefix: {options['prefix']}  |  "
            f"min-kb: {options['min_kb']}  |  "
            f"candidates: {len(candidates)} "
            f"(below threshold and skipped: {below_threshold})"
        )
        self.stdout.write("-" * 80)

        if cache_only:
            self._run_cache_only(s3, bucket, candidates, options)
        else:
            self._run_reencode(s3, bucket, candidates, dry, limit)

    def _run_reencode(self, s3, bucket, candidates, dry, limit):
        stats = {
            "processed": 0,
            "skipped_bigger": 0,
            "skipped_error": 0,
            "total_before": 0,
            "total_after": 0,
        }

        started = time.time()
        for cand in candidates:
            if limit and stats["processed"] >= limit:
                break
            self._process_one(s3, bucket, cand, stats, dry)

        elapsed = time.time() - started

        self.stdout.write("-" * 80)
        tb = stats["total_before"]
        ta = stats["total_after"]
        saved = tb - ta
        pct = (saved / tb * 100) if tb else 0
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Would process' if dry else 'Processed'}: {stats['processed']}  |  "
                f"skipped (no improvement): {stats['skipped_bigger']}  |  "
                f"errors: {stats['skipped_error']}  |  "
                f"elapsed: {elapsed:.1f}s"
            )
        )
        if stats["processed"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Total: {tb // 1024} KB -> {ta // 1024} KB  "
                    f"(saved {saved // 1024} KB, -{pct:.0f}%)"
                )
            )

    def _run_cache_only(self, s3, bucket, candidates, options):
        dry = options["dry_run"]
        limit = options["limit"]
        force = options["force"]

        stats = {
            "updated": 0,
            "already_ok": 0,
            "skipped_error": 0,
        }

        started = time.time()
        for cand in candidates:
            if limit and stats["updated"] >= limit:
                break
            self._process_cache_only(s3, bucket, cand, stats, dry, force)

        elapsed = time.time() - started

        self.stdout.write("-" * 80)
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Would update' if dry else 'Updated'}: {stats['updated']}  |  "
                f"already OK: {stats['already_ok']}  |  "
                f"errors: {stats['skipped_error']}  |  "
                f"elapsed: {elapsed:.1f}s"
            )
        )

    def _collect_candidates(self, s3, bucket, options):
        """Return list of {'key': str, 'size': int} to consider."""
        if options["key"]:
            try:
                head = s3.head_object(Bucket=bucket, Key=options["key"])
            except ClientError as exc:
                raise CommandError(f"Cannot HEAD {options['key']}: {exc}")
            return [{"key": options["key"], "size": head["ContentLength"]}]

        if options["slug"]:
            from apps.strains.models import Strain

            strain = Strain.objects.filter(slug=options["slug"]).first()
            if strain is None:
                raise CommandError(f"No Strain with slug '{options['slug']}'")
            if not strain.img:
                raise CommandError(f"Strain '{options['slug']}' has no image")
            key = f"{settings.PUBLIC_MEDIA_LOCATION}/{strain.img.name}"
            try:
                head = s3.head_object(Bucket=bucket, Key=key)
            except ClientError as exc:
                raise CommandError(f"Cannot HEAD {key}: {exc}")
            return [{"key": key, "size": head["ContentLength"]}]

        prefix = options["prefix"]
        paginator = s3.get_paginator("list_objects_v2")
        items = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                items.append({"key": obj["Key"], "size": obj["Size"]})
        items.sort(key=lambda x: -x["size"])
        return items

    def _process_one(self, s3, bucket, cand, stats, dry):
        key = cand["key"]
        size = cand["size"]
        short = key.split("/")[-1]
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            original = obj["Body"].read()
        except ClientError as exc:
            self.stderr.write(f"  [error] GET {short}: {exc}")
            stats["skipped_error"] += 1
            return

        try:
            new_bytes, new_ct, fmt = _reencode(original)
        except Exception as exc:
            self.stderr.write(f"  [error] reencode {short}: {exc}")
            stats["skipped_error"] += 1
            return

        new_size = len(new_bytes)
        if new_size >= size:
            self.stdout.write(
                f"  [skip]  {short:<50}  {size // 1024:>5} KB ->"
                f" {new_size // 1024:>5} KB  (no improvement)"
            )
            stats["skipped_bigger"] += 1
            return

        pct = (size - new_size) / size * 100
        self.stdout.write(
            f"  [{'dry' if dry else 'ok '}]  {short:<50}  "
            f"{size // 1024:>5} KB -> {new_size // 1024:>5} KB  "
            f"(-{(size - new_size) // 1024:>4} KB, -{pct:>2.0f}%, {fmt})"
        )
        stats["total_before"] += size
        stats["total_after"] += new_size
        stats["processed"] += 1

        if dry:
            return

        try:
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=new_bytes,
                ContentType=new_ct,
                CacheControl=LONG_CACHE,
            )
        except ClientError as exc:
            self.stderr.write(f"  [error] PUT {short}: {exc}")
            stats["skipped_error"] += 1
            stats["total_before"] -= size
            stats["total_after"] -= new_size
            stats["processed"] -= 1

    def _process_cache_only(self, s3, bucket, cand, stats, dry, force):
        """Rewrite Cache-Control via S3 CopyObject without re-encoding the body.

        HEADs the object first to (a) preserve the existing ContentType when
        copying with MetadataDirective=REPLACE, and (b) skip files that already
        have the target Cache-Control unless --force was passed.
        """
        key = cand["key"]
        short = key.split("/")[-1]

        try:
            head = s3.head_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            self.stderr.write(f"  [error] HEAD {short}: {exc}")
            stats["skipped_error"] += 1
            return

        current_cc = head.get("CacheControl") or ""
        ct = head.get("ContentType") or _guess_content_type(key)

        if not force and _normalize_cc(current_cc) == _normalize_cc(LONG_CACHE):
            self.stdout.write(f"  [keep]  {short:<60}  cc='{current_cc}'")
            stats["already_ok"] += 1
            return

        self.stdout.write(
            f"  [{'dry' if dry else 'ok '}]  {short:<60}  "
            f"cc='{current_cc or '<none>'}' -> '{LONG_CACHE}'  ct='{ct}'"
        )

        if dry:
            stats["updated"] += 1
            return

        copy_kwargs = {
            "CopySource": {"Bucket": bucket, "Key": key},
            "Bucket": bucket,
            "Key": key,
            "MetadataDirective": "REPLACE",
            "CacheControl": LONG_CACHE,
            "ContentType": ct,
        }
        # Preserve a few related headers when present so they aren't dropped by
        # MetadataDirective=REPLACE.
        for src_field, dst_field in (
            ("ContentDisposition", "ContentDisposition"),
            ("ContentEncoding", "ContentEncoding"),
            ("ContentLanguage", "ContentLanguage"),
        ):
            value = head.get(src_field)
            if value:
                copy_kwargs[dst_field] = value
        user_meta = head.get("Metadata") or {}
        if user_meta:
            copy_kwargs["Metadata"] = user_meta

        try:
            s3.copy_object(**copy_kwargs)
        except ClientError as exc:
            self.stderr.write(f"  [error] COPY {short}: {exc}")
            stats["skipped_error"] += 1
            return

        stats["updated"] += 1


_EXT_TO_CT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
}


def _guess_content_type(key: str) -> str:
    suffix = Path(key).suffix.lower()
    return _EXT_TO_CT.get(suffix, "application/octet-stream")


def _normalize_cc(value: str) -> str:
    """Normalize Cache-Control for idempotent comparison.

    'public, max-age=31536000, immutable' and 'public,max-age=31536000,immutable'
    are equivalent — strip whitespace around commas and lowercase.
    """
    return ",".join(part.strip().lower() for part in value.split(",") if part.strip())
