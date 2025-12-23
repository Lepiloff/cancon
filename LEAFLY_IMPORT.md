# Leafly Strain Import

## Purpose
Automate importing cannabis strains from Leafly into the project database. The flow fetches a Leafly strain page by alias, extracts structured data, generates unique English copy, translates it to Spanish, and persists the strain with related taxonomies.

## What Gets Created
- Strain with SEO fields and content:
  - `title`, `description`, `keywords` in EN/ES (deterministic templates)
  - `text_content` as a single `<p>...</p>` block (no Leafly links)
  - `img_alt_text` in EN/ES
- Core strain attributes:
  - `name`, `category`, `rating`, `thc`, `cbd`, `cbg`
  - `active` = `False`, `is_review` = `False`
  - `img` = random existing strain image
- Related taxonomies:
  - Feelings (effects), Negatives, HelpsWith, Flavors
  - Terpenes: first is dominant, the rest are "other"
- Alternative names:
  - Added only if explicitly detected in the Leafly description (e.g., "also known as")

## Data Source & Parsing
- Leafly pages are fetched via: `https://www.leafly.com/strains/<alias>`
- Primary extraction uses embedded structured data from the page.
- Fallback parsing from HTML is used if structured data is missing.
- Top ranked traits are selected by Leafly scores (defaults):
  - Effects: 3
  - Negatives: 3
  - Flavors: 3
  - HelpsWith: 4
  - Terpenes: 3

## Command Usage
```
python manage.py import_leafly_strains lemon-cherry-gelato og-kush --pause 5
```

Options:
- `--alias-file /path/to/aliases.txt` (one alias per line)
- `--pause 5.0` (delay between Leafly requests)
- `--timeout 15` (HTTP timeout)
- `--retries 2` (HTTP retries)
- `--dry-run` (no DB writes)

## Skip Rules
If a strain already exists by:
- `Strain.name` (case-insensitive), or
- `AlternativeStrainName.name` (case-insensitive)
then the import is skipped.

## Translation & Copywriting
- English copy is generated via OpenAI based on Leafly facts.
- Spanish translation uses existing translation service.
- Only `text_content` and `img_alt_text` are translated automatically.
- Strain names and genetics references are preserved exactly.

## Console Output
Each stage reports success or failure:
- fetch, parse, copy, translate, taxonomy assignment, save
Final summary shows counts for created/skipped/failed.

## Configuration Requirements
Environment variables used:
- `OPENAI_API_KEY`
- `OPENAI_AGENT_MODEL` (default `gpt-4o-mini`)
- `AGENT_TEMPERATURE`

## Database Change
`Strain.rating` is now nullable to support missing ratings.
Run migrations:
```
python manage.py migrate
```

## Notes
- Existing strains are never updated by this command.
- If you need to refresh an imported strain, delete it first and re-run.
