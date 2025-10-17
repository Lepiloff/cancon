# Translation Service

AI-powered translation service using OpenAI GPT-4o-mini for automatic content translation.

## Features

- ✅ **Phase 2 Complete**: Bulk translation of existing content (ES→EN or EN→ES)
- ✅ **Phase 3 Complete**: Automatic translation on save (synchronous)
- 🏗️ **Architecture**: SOLID principles, DRY, modular design
- 🔧 **No AWS required**: Works with direct OpenAI API calls

## Quick Start

### 1. Configuration

Add to your `.env`:

```bash
# OpenAI Configuration (required)
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_AGENT_MODEL=gpt-4o-mini
AGENT_TEMPERATURE=0.3

# Translation Settings (optional)
ENABLE_AUTO_TRANSLATION=true
TRANSLATION_DIRECTION=en-to-es  # or es-to-en
TRANSLATION_PAUSE_SECONDS=1.5
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Phase 2: Bulk Translation

Translate all existing Spanish content to English:

```bash
# Production (via Docker)
docker-compose exec web python manage.py translate_existing_content --direction es-to-en

# Local
python manage.py translate_existing_content --direction es-to-en
```

**Options:**
```bash
# Dry run (see what will be translated)
python manage.py translate_existing_content --direction es-to-en --dry-run

# Translate only Strain model
python manage.py translate_existing_content --direction es-to-en --model Strain

# Limit to first 10 items (for testing)
python manage.py translate_existing_content --direction es-to-en --limit 10

# Force retranslate even if target exists
python manage.py translate_existing_content --direction es-to-en --force

# Custom pause between API calls (seconds)
python manage.py translate_existing_content --direction es-to-en --pause 2.0
```

### 4. Phase 3: Automatic Translation

Once Phase 2 is complete, automatic translation will work on save in admin:

1. **Change direction** in `.env`:
   ```bash
   TRANSLATION_DIRECTION=en-to-es
   ```

2. **Add/Edit content** in admin:
   - Fill English fields (EN tab)
   - Click Save
   - Spanish translation happens automatically (3-5 seconds)
   - Check ES tab for results

**Disable auto-translation temporarily:**
```bash
ENABLE_AUTO_TRANSLATION=false
```

## Management Commands

### Check Translation Status

```bash
python manage.py check_translations

# Check specific model
python manage.py check_translations --model Strain

# Fix outdated translations
python manage.py check_translations --fix
```

### Retry Failed Translations

```bash
python manage.py retry_failed_translations

# Retry up to 50
python manage.py retry_failed_translations --max 50

# Retry only Articles
python manage.py retry_failed_translations --model Article
```

## Architecture

### Structure

```
apps/translation/
├── __init__.py
├── apps.py
├── config.py              # Configuration (TranslationConfig)
├── base_translator.py     # Abstract base class
├── openai_translator.py   # OpenAI implementation
├── prompts.py            # Translation prompts
└── README.md
```

### Key Classes

- **`TranslationConfig`**: Centralized configuration
- **`BaseTranslator`**: Abstract interface (Liskov Substitution Principle)
- **`OpenAITranslator`**: OpenAI implementation
- **`TranslationPrompts`**: Prompt management (Open/Closed Principle)

### Models with Translation

- **Strain**: `title`, `description`, `text_content`, `keywords`, `img_alt_text`
- **Article**: `title`, `description`, `text_content`, `keywords`
- **Terpene**: `description`

## Translation Rules

### Preserved (Never Translated)

✅ Strain names: "Northern Lights", "OG Kush"
✅ Terpene names: "Limonene", "Myrcene"
✅ HTML tags: `<p>`, `<h3>`, `<strong>`
✅ URLs and links
✅ Measurement units: %, mg/g, THC, CBD
✅ Genetic terms: Indica, Sativa, Hybrid

### Translated

🌐 Content fields (title, description, text_content)
🌐 Effects and feelings
🌐 Image alt text (for accessibility)

## Cost Estimation

### OpenAI API (gpt-4o-mini)

- **Input**: $0.150 / 1M tokens
- **Output**: $0.600 / 1M tokens
- **Average strain**: ~650 input + 700 output tokens = **$0.008**

### Monthly Costs

- 100 new strains/month: **~$0.80/month**
- One-time bulk (1000 items): **~$8**

## Troubleshooting

### "OPENAI_API_KEY not set"

Add to `.env`:
```bash
OPENAI_API_KEY=sk-proj-xxxxx
```

### Translation fails with rate limit error

Increase pause between requests:
```bash
python manage.py translate_existing_content --direction es-to-en --pause 2.5
```

Or in `.env`:
```bash
TRANSLATION_PAUSE_SECONDS=2.5
```

### Auto-translation not working

1. Check settings:
   ```python
   # In Django shell
   from django.conf import settings
   print(settings.ENABLE_AUTO_TRANSLATION)  # Should be True
   print(settings.TRANSLATION_DIRECTION)     # Should be 'en-to-es'
   ```

2. Check signals are registered:
   ```python
   from django.db.models.signals import post_save
   from apps.strains.models import Strain
   print(post_save.has_listeners(Strain))  # Should be True
   ```

3. Check logs:
   ```bash
   # In Docker
   docker-compose logs web | grep -i translation
   ```

### Translation quality issues

Edit the translation manually in admin:
1. Go to object in admin
2. Click ES tab
3. Edit translated content
4. Save

The system will not overwrite manual edits unless content changes.

## Production Deployment

### Step 1: Deploy Code

```bash
# Push to production
git add .
git commit -m "Add AI translation system (Phase 2 & 3)"
git push origin feature/multilanguage
```

### Step 2: Install Dependencies

```bash
# On EC2 via SSH
docker-compose exec web pip install -r requirements.txt
```

### Step 3: Run Bulk Translation

```bash
# Test with dry-run first
docker-compose exec web python manage.py translate_existing_content --direction es-to-en --dry-run

# Run actual translation
docker-compose exec web python manage.py translate_existing_content --direction es-to-en
```

**Monitor progress** (~15-20 minutes for 1000 items):
- Console shows real-time progress
- Can be interrupted (Ctrl+C) and resumed

### Step 4: Switch Direction

After bulk translation completes, update `.env`:

```bash
TRANSLATION_DIRECTION=en-to-es
```

Restart application:
```bash
docker-compose restart web
```

### Step 5: Test Auto-Translation

1. Go to admin
2. Create/edit a Strain with English content
3. Save
4. Check that Spanish translation appears (may take 3-5 seconds)

## Support

For issues or questions, check:
- `ADMIN_GUIDE.md` - For content managers
- `AI_TRANSLATION_SETUP.md` - Technical setup guide
- Django logs - For error messages

## Version

- **Version**: 1.0
- **Last Updated**: 2025-10-10
- **OpenAI Version**: 2.3.0
- **Python**: 3.10+
- **Django**: 4.2.16
