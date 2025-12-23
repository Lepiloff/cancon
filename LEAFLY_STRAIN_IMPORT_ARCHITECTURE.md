# Leafly Strain Ingestion - Proposed Architecture

## Goals
- Add a Django management command to import strains from Leafly by alias list.
- Parse Leafly strain pages into normalized data for Strain and related models.
- Generate unique, SEO-optimized English copy, then translate to Spanish using the existing translation service.
- Enforce a 5 second delay between Leafly requests to avoid throttling.
- Skip existing strains if a match is found by name or alias.
- Preserve genetics references and related strain names in generated copy.
- Do not include Leafly links in saved `text_content`.

## Data Flow
1. Management command receives a list of Leafly aliases (URL slugs).
2. For each alias:
   - Check for existing Strain by `name` or `AlternativeStrainName` match; skip if found.
   - Fetch `https://www.leafly.com/strains/<alias>` with a browser-like User-Agent.
   - Parse the page into raw data (name, category, rating, THC/CBD/CBG, description, effects, negatives, helps_with, flavors, terpenes).
   - Run OpenAI copywriting to produce English content fields and detect alternative names.
   - Translate `text_content` and `img_alt_text` to Spanish using `apps.translation.OpenAITranslator`.
   - Create Strain and related models; set `active=False`, `is_review=False`, and a random existing image.
   - Sleep 5 seconds before the next Leafly request.

## Components
- LeaflyClient
  - `requests.get` with retry/backoff for 429/5xx.
  - Configurable timeout and headers.
- LeaflyParser
  - Primary: parse `__NEXT_DATA__` or JSON embedded in the page.
  - Fallback: parse HTML via CSS selectors if JSON is missing.
  - Output: a normalized dict for all fields needed by Strain and related models.
- CopywritingService
  - OpenAI chat completion with a strict JSON schema output.
  - Generates: `text_content` (HTML), `img_alt_text`.
  - Extracts `alternative_names` when the Leafly description indicates "also known as ...".
  - Preserves genetics references and parent strains mentioned in the Leafly description.
  - Produces `text_content` as a single `<p>...</p>` block with length similar to Leafly.
  - Enforces ASCII punctuation and HTML-safe content.
- TranslationService
  - Uses `apps.translation.OpenAITranslator.translate` for en-to-es.
  - Translates `text_content` and `img_alt_text` only.
  - Sets translation metadata (`translation_status`, `translation_source_hash`, `last_translated_at`) to avoid auto-translation signals re-running.
- StrainPersister
  - Skips write if existing Strain matched by name or alias.
  - Creates `Strain` with English fields in both base and `_en` columns.
  - Saves Spanish fields in `_es` columns (meta fields generated deterministically).
  - Resolves M2M relations via `get_or_create` for Feeling, Negative, HelpsWith, Flavor.
  - Auto-translates taxonomy `name_es` for newly created Feeling/Negative/HelpsWith/Flavor.
  - Sets `dominant_terpene` (first in list) and `other_terpenes`.
  - Creates `AlternativeStrainName` entries only from LLM-detected names.
  - Assigns a random existing `Strain.img` if available.
  - Leaves `canonical_url` as null.

## Field Mapping (Leafly -> DB)
- name -> `Strain.name`
- category -> `Strain.category` (map to `Hybrid`, `Indica`, `Sativa`)
- rating -> `Strain.rating` (nullable if not present)
- thc/cbd/cbg -> `Strain.thc`, `Strain.cbd`, `Strain.cbg` (numeric)
- effects/feelings -> `Strain.feelings`
- negatives -> `Strain.negatives`
- helps_with -> `Strain.helps_with`
- flavors -> `Strain.flavors`
- terpene list -> `Strain.dominant_terpene`, `Strain.other_terpenes`
- description text + strain metadata -> OpenAI copywriting input
- alternative names -> `AlternativeStrainName` (from LLM output)

## SEO Patterns
- Title (EN): `{Strain name} | Weed Strain`
- Title (ES): `{Strain name} | Variedad de Cannabis`
- Description (EN): `Learn more about the {name} weed strain, its effects and flavors.`
- Description (ES): `Información sobre la variedad de cannabis {name}, sus efectos y sabores.`
- Keywords (EN): `{name}, cannabis, strain, effects, flavors`
- Keywords (ES): `{name}, cannabis, variedad, efectos, sabores`

## Command Interface (Proposed)
```
python manage.py import_leafly_strains lemon-cherry-gelato og-kush
```
Optional flags:
- `--pause 5.0` (override Leafly request delay)
- `--dry-run` (no DB writes)
- `--alias-file /path/to/aliases.txt`

## Error Handling
- Fetch/parse errors: log and skip to next alias.
- OpenAI failures: record in logs and skip DB write for that alias.
- DB errors: wrap per-strain in a transaction to avoid partial writes.
- Console output for each stage (fetch, parse, copywriting, translation, save) with success/failure status.

## Configuration
- Uses existing OpenAI env vars:
  - `OPENAI_API_KEY`, `OPENAI_AGENT_MODEL`, `AGENT_TEMPERATURE`
- Optional new env vars:
  - `LEAFLY_REQUEST_TIMEOUT`, `LEAFLY_REQUEST_RETRIES`
  - `LEAFLY_PAUSE_SECONDS` (default 5.0)

## Assumptions / Open Questions
- None (requirements confirmed).
