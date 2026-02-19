#!/usr/bin/env python3
"""
Scrape all strain slugs from Leafly.com and output those missing from our DB.

Usage:
    # Scrape everything (auto-resumes from last checkpoint):
    python scripts/scrape_leafly_slugs.py

    # Skip DB comparison (faster, just collect slugs):
    python scripts/scrape_leafly_slugs.py --no-db

    # Stop after N pages (save & resume later):
    python scripts/scrape_leafly_slugs.py --stop-after 50

    # Reset and start from scratch:
    python scripts/scrape_leafly_slugs.py --reset

Output:
    scripts/output/batches/leafly_p0001-0050.txt  — slugs per 50-page batch
    scripts/output/batches/leafly_p0051-0100.txt
    ...
    scripts/output/leafly_all_aliases.txt          — all slugs combined
    scripts/output/leafly_missing_aliases.txt      — slugs not in DB
    scripts/output/leafly_progress.txt             — last completed page (for resuming)
"""

import argparse
import json
import os
import re
import sys
import time

import requests

LEAFLY_STRAINS_URL = 'https://www.leafly.com/strains'
BATCH_SIZE = 50  # pages per batch file

OUTPUT_DIR      = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
BATCHES_DIR     = os.path.join(OUTPUT_DIR, 'batches')
OUTPUT_ALL      = os.path.join(OUTPUT_DIR, 'leafly_all_aliases.txt')
OUTPUT_MISSING  = os.path.join(OUTPUT_DIR, 'leafly_missing_aliases.txt')
OUTPUT_SKIPPED  = os.path.join(OUTPUT_DIR, 'leafly_skipped_aliases.txt')
OUTPUT_PROGRESS = os.path.join(OUTPUT_DIR, 'leafly_progress.txt')

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
})


# ─── Leafly fetching ───────────────────────────────────────────────────────────

def fetch_page(page: int, retries: int = 3) -> dict | None:
    """Fetch a single Leafly strains page and return parsed __NEXT_DATA__."""
    url = f'{LEAFLY_STRAINS_URL}?page={page}'
    for attempt in range(retries):
        try:
            resp = SESSION.get(url, timeout=20)
            if resp.status_code == 200:
                match = re.search(
                    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                    resp.text, re.S,
                )
                if not match:
                    match = re.search(
                        r'__NEXT_DATA__["\s].*?type="application/json">(.*?)</script>',
                        resp.text, re.S,
                    )
                if match:
                    return json.loads(match.group(1))
                print(f'  [warn] No __NEXT_DATA__ on page {page}')
                return None
            if resp.status_code in (429, 500, 502, 503):
                wait = 2 ** (attempt + 1)
                print(f'  [retry] Page {page}: HTTP {resp.status_code}, waiting {wait}s')
                time.sleep(wait)
                continue
            print(f'  [error] Page {page}: HTTP {resp.status_code}')
            return None
        except requests.RequestException as exc:
            wait = 2 ** (attempt + 1)
            print(f'  [retry] Page {page}: {exc}, waiting {wait}s')
            time.sleep(wait)
    return None


def extract_slugs(next_data: dict) -> list[str]:
    try:
        strains = next_data['props']['pageProps']['data']['strains']
        return [s['slug'] for s in strains if s.get('slug')]
    except (KeyError, TypeError):
        try:
            strains = next_data['props']['pageProps']['strains']
            return [s['slug'] for s in strains if s.get('slug')]
        except (KeyError, TypeError):
            return []


def get_total_pages(next_data: dict) -> int:
    try:
        total = next_data['props']['pageProps']['data']['totalCount']
        per_page = len(extract_slugs(next_data)) or 18
        return (total + per_page - 1) // per_page
    except (KeyError, TypeError):
        return 493


# ─── File helpers ──────────────────────────────────────────────────────────────

def batch_filepath(batch_start: int, batch_end: int) -> str:
    return os.path.join(BATCHES_DIR, f'leafly_p{batch_start:04d}-{batch_end:04d}.txt')


def save_batch_file(batch_start: int, batch_end: int, slugs: list[str]) -> None:
    """Save slugs for one 50-page batch into its own file."""
    os.makedirs(BATCHES_DIR, exist_ok=True)
    path = batch_filepath(batch_start, batch_end)
    with open(path, 'w') as f:
        f.write('\n'.join(slugs) + '\n')
    print(f'  [batch] Saved {len(slugs)} slugs → {os.path.relpath(path)}')


def load_progress() -> tuple[int, list[str]]:
    """Return (last_completed_page, all_slugs_so_far)."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    last_page = 0
    all_slugs: list[str] = []

    if os.path.exists(OUTPUT_PROGRESS):
        try:
            with open(OUTPUT_PROGRESS) as f:
                last_page = int(f.read().strip())
        except ValueError:
            last_page = 0

    if os.path.exists(OUTPUT_ALL) and last_page > 0:
        with open(OUTPUT_ALL) as f:
            all_slugs = [ln.strip() for ln in f if ln.strip()]
        print(f'[resume] Resuming from page {last_page + 1} ({len(all_slugs)} slugs already collected)')

    return last_page, all_slugs


def save_progress(last_page: int, slugs: list[str]) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_PROGRESS, 'w') as f:
        f.write(str(last_page))
    with open(OUTPUT_ALL, 'w') as f:
        f.write('\n'.join(slugs) + '\n')


# ─── DB helpers ────────────────────────────────────────────────────────────────

def get_existing_slugs_from_db() -> set[str]:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'canna.settings')
    import django
    django.setup()
    from apps.strains.models import Strain, AlternativeStrainName

    existing: set[str] = set()
    for name, slug in Strain.objects.values_list('name', 'slug'):
        existing.add(name.lower())
        existing.add(slug.lower())
        existing.add(name.lower().replace(' ', '-').replace("'", ''))
    for name in AlternativeStrainName.objects.values_list('name', flat=True):
        existing.add(name.lower())
        existing.add(name.lower().replace(' ', '-').replace("'", ''))

    # Also exclude aliases that were quality-filtered (too sparse / no reviews).
    # These are written by import_leafly_strains after each batch.
    if os.path.exists(OUTPUT_SKIPPED):
        with open(OUTPUT_SKIPPED) as f:
            skipped = [ln.strip().lower() for ln in f if ln.strip()]
        existing.update(skipped)
        print(f'Quality-filtered (skip file): {len(skipped)} aliases excluded')

    return existing


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Scrape all Leafly strain slugs')
    parser.add_argument('--no-db', action='store_true', help='Skip DB comparison at the end')
    parser.add_argument('--pause', type=float, default=1.5,
                        help='Pause between page requests in seconds (default: 1.5)')
    parser.add_argument('--stop-after', type=int, default=0,
                        help='Stop after this many pages from start (0 = run all)')
    parser.add_argument('--start-page', type=int, default=0,
                        help='Force start from this page (default: auto from progress)')
    parser.add_argument('--reset', action='store_true',
                        help='Clear all progress and start from scratch')
    args = parser.parse_args()

    # ── Reset ──
    if args.reset:
        for path in [OUTPUT_PROGRESS, OUTPUT_ALL, OUTPUT_MISSING]:
            if os.path.exists(path):
                os.remove(path)
        print('[reset] Progress cleared, starting from scratch')

    # ── Load checkpoint ──
    last_completed, all_slugs = load_progress()
    start_page = args.start_page if args.start_page > 0 else last_completed + 1

    # ── Fetch page 1 (always needed to get total_pages) ──
    if start_page == 1:
        print('Fetching page 1...')
        first_data = fetch_page(1)
        if not first_data:
            print('ERROR: Failed to fetch page 1')
            sys.exit(1)
        total_pages = get_total_pages(first_data)
        page1_slugs = extract_slugs(first_data)
        all_slugs.extend(page1_slugs)
        print(f'  Page 1: {len(page1_slugs)} strains | total pages: {total_pages}')
        save_progress(1, all_slugs)
        start_page = 2
    else:
        print(f'Fetching page 1 to get total pages...')
        first_data = fetch_page(1)
        total_pages = get_total_pages(first_data) if first_data else 493

    end_page = total_pages
    if args.stop_after > 0:
        end_page = min(total_pages, start_page + args.stop_after - 1)

    if start_page > total_pages:
        print(f'Already scraped all {total_pages} pages. Nothing to do.')
    else:
        print(f'Scraping pages {start_page}–{end_page} / {total_pages}  (pause={args.pause}s)')
        print(f'Per-batch files will be saved every {BATCH_SIZE} pages → {os.path.relpath(BATCHES_DIR)}/')
        print()

        # Track slugs collected in the current 50-page window
        # Figure out which batch window we're starting in
        def batch_window(page: int) -> tuple[int, int]:
            """Return (batch_start, batch_end) for the 50-page window containing page."""
            b = ((page - 1) // BATCH_SIZE) * BATCH_SIZE + 1
            return b, b + BATCH_SIZE - 1

        current_batch_start, current_batch_end = batch_window(start_page)
        current_batch_slugs: list[str] = []

        for page in range(start_page, end_page + 1):
            if args.pause > 0:
                time.sleep(args.pause)

            data = fetch_page(page)
            if not data:
                print(f'  Page {page}: FAILED (skipping)')
            else:
                slugs = extract_slugs(data)
                all_slugs.extend(slugs)
                current_batch_slugs.extend(slugs)

            # End of a 50-page batch window?
            _, win_end = batch_window(page)
            is_batch_boundary = (page == win_end) or (page == end_page)

            if is_batch_boundary and current_batch_slugs:
                # Deduplicate batch slugs
                seen: set[str] = set()
                unique_batch: list[str] = []
                for s in current_batch_slugs:
                    if s.lower() not in seen:
                        seen.add(s.lower())
                        unique_batch.append(s)

                save_batch_file(current_batch_start, page, unique_batch)
                save_progress(page, all_slugs)

                # Move to next batch window
                current_batch_start, current_batch_end = batch_window(page + 1)
                current_batch_slugs = []
            elif page % 10 == 0:
                # Checkpoint every 10 pages (no batch file yet)
                save_progress(page, all_slugs)

            if page % 50 == 0 or page == end_page:
                print(f'  Page {page}/{total_pages}: total slugs so far = {len(all_slugs)}')

        # Final progress save
        save_progress(end_page, all_slugs)

        remaining = total_pages - end_page
        if remaining > 0:
            print(f'\n[done] Stopped at page {end_page}. {remaining} pages remaining.')
            print(f'Resume: python scripts/scrape_leafly_slugs.py')
        else:
            print(f'\n[done] All {total_pages} pages scraped!')

    # ── Deduplicate all_aliases ──
    seen: set[str] = set()
    unique_all: list[str] = []
    for s in all_slugs:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique_all.append(s)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_ALL, 'w') as f:
        f.write('\n'.join(unique_all) + '\n')
    print(f'\nTotal unique slugs: {len(unique_all)}')
    print(f'All slugs: {OUTPUT_ALL}')

    # ── DB comparison ──
    if not args.no_db:
        print('\nComparing with database...')
        existing = get_existing_slugs_from_db()
        print(f'Existing in DB: {len(existing)} entries')
        missing = [s for s in unique_all if s.lower() not in existing]
        print(f'Missing (not in DB): {len(missing)}')
        with open(OUTPUT_MISSING, 'w') as f:
            f.write('\n'.join(missing) + '\n')
        print(f'Missing slugs: {OUTPUT_MISSING}')
        print(f'\nImport command:')
        print(f'  python manage.py import_leafly_strains --alias-file {OUTPUT_MISSING} --pause 5')
    else:
        print(f'DB comparison skipped (--no-db)')


if __name__ == '__main__':
    main()
