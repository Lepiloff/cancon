# Admin Guide: Bilingual Content Management
**For Content Managers and Admins**

---

## Quick Reference

### Current Setup

**What's Available:**
- Language tabs in admin forms (EN/ES)
- Language switcher on frontend (🇬🇧 EN / 🇪🇸 ES)
- Automatic AI translation (EN→ES and ES→EN)
- Skip translation checkbox for minor edits
- Taxonomy (Feelings, Flavors, etc.) has both EN and ES

---

## How to Edit Content

### Admin Language Tabs

When editing Strains, Articles, or Terpenes, you'll see **language tabs** above translatable fields:

```
┌─────────────────────────────────────┐
│  Title                              │
│  ┌──────┬──────┐                   │
│  │  EN  │  ES  │                   │
│  └──────┴──────┘                   │
│  [Content here...]                  │
└─────────────────────────────────────┘
```

**To edit:**
1. Click **EN** tab → edit English version
2. Click **ES** tab → edit Spanish version
3. Click **Save** → both versions saved

### Translation Status Badges

In list views, you'll see colored badges:

- 🟢 **Synced** - Translation up to date
- 🟡 **Pending** - Waiting for translation
- 🔴 **Outdated** - Needs re-translation (content changed)
- ⚫ **Failed** - Translation error (check admin)

### Skip Translation Checkbox (NEW!)

**When editing content, you'll see a checkbox at the bottom of the form:**

```
┌─────────────────────────────────────────────────┐
│  Title (EN): ...                                │
│  Description (EN): ...                          │
│  Text content (EN): ...                         │
│                                                 │
│  ☐ Skip translation (minor edit)               │ ← NEW!
│     ✓ Check this if you made small changes     │
│     (typo, formatting) and don't need           │
│     re-translation. Leave unchecked for         │
│     content changes that need translation.      │
│                                                 │
│  [Save]  [Save and continue]  [Delete]          │
└─────────────────────────────────────────────────┘
```

**When to check this box:**
- ✅ Fixed a typo or spelling error
- ✅ Changed HTML formatting (h1 → h2, bold → italic)
- ✅ Adjusted spacing or line breaks
- ✅ Minor style changes
- ✅ Updated image URLs

**When to leave it UNCHECKED:**
- ❌ Added new sentences or paragraphs
- ❌ Changed meaning of text
- ❌ Updated product information
- ❌ Modified keywords or descriptions

**What happens when checked:**
- Translation does NOT run
- Status stays "Synced" (no re-translation needed)
- Your changes are saved immediately

**What happens when unchecked:**
- Translation runs automatically (~30 seconds)
- Status changes to "Outdated" → "Synced"
- Other language version is updated

**💡 Pro Tip:** HTML formatting changes (like `<h1>` → `<h2>`) are automatically detected and won't trigger re-translation even if you forget to check the box!

### Force Retranslate

If you need to re-translate an item:

1. Select items in list view
2. Choose "Force retranslate selected items" from Actions dropdown
3. Click "Go"

---

## What Gets Translated

### ✅ Translated Fields

**Strains:**
- Title (meta title for SEO)
- Description (meta description)
- Text Content (full article)
- Keywords (SEO keywords)
- Image Alt Text (for accessibility)

**NOT translated:** Strain name (e.g., "White Widow" stays in English)

**Articles:**
- Title
- Description
- Text Content
- Keywords

**Terpenes:**
- Description (effects, benefits)

**NOT translated:** Terpene name (e.g., "Limonene" stays in English)

**Taxonomy (Feelings, Flavors, Negatives, Helps With):**
- Name (e.g., "Happy" → "Feliz")

### ❌ NOT Translated

- Strain names ("OG Kush", "Northern Lights")
- Terpene names ("Myrcene", "Pinene")
- Article Category names
- Article image alt text (not critical for SEO)

---

## Frontend Language Switching

Users can switch languages via dropdown in header:

🇬🇧 EN / 🇪🇸 ES

**Default:** Spanish (ES)

**How it works:**
- Changes UI text ("Variedades", "Sensaciones" → "Strains", "Feelings")
- Changes database content (Strain.title_es → Strain.title_en)
- Both change together automatically

---

## Workflow Guide

### Workflow 1: Creating New Content (with Auto-Translation)

1. **Create new item:**
   - Go to admin → Strains/Articles/Terpenes
   - Click "Add New"

2. **Fill in English content (EN tab):**
   - Click EN tab
   - Write all content in English
   - Fill all required fields

3. **Save (leave checkbox UNCHECKED):**
   - Leave "Skip translation" unchecked
   - Click "Save"
   - ⏱️ Wait ~30 seconds for AI translation

4. **Review Spanish translation (ES tab):**
   - Click ES tab
   - Check translation quality
   - Edit if needed
   - Save again (you can check "Skip translation" if only fixing translation)

5. **Verify on Frontend:**
   - Use language switcher to check both versions

### Workflow 2: Minor Edits (Skip Translation)

**Example: You found a typo in English content**

1. **Open item for editing:**
   - Find the item in admin list
   - Click to edit

2. **Fix the typo:**
   - EN tab: Fix "teh" → "the"

3. **Check "Skip translation" box:**
   - ☑ Check the checkbox at bottom
   - Reason: Typo fix doesn't need re-translation

4. **Save:**
   - Click "Save"
   - ✅ Instant save

### Workflow 3: HTML Formatting Changes

**Example: You want to change h1 to h2**

1. **Edit content:**
   - EN tab: `<h1>Title</h1>` → `<h2>Title</h2>`

2. **Save (checkbox optional):**
   - You can leave checkbox unchecked
   - System automatically detects it's only HTML change
   - Won't trigger re-translation ✅

**Note:** This works for: h1↔h2↔h3, bold↔italic, p↔div, spacing changes

### Workflow 4: Content Updates (Need Translation)

**Example: Adding new paragraph to article**

1. **Edit content:**
   - EN tab: Add new paragraph with product info

2. **Save (leave checkbox UNCHECKED):**
   - Don't check "Skip translation"
   - Click "Save"
   - ⏱️ Translation runs automatically

3. **Review translation:**
   - Check ES tab after ~30 seconds
   - Verify quality

### Quick Decision Chart

**Should I check "Skip translation"?**

```
Did you change actual TEXT content?
├─ YES → Leave UNCHECKED (needs translation)
│   Examples: new sentences, changed wording, updated info
│
└─ NO → Check ☑ SKIP (no translation needed)
    Examples: fixed typo, changed h1→h2, spacing
```

---

## Search & Filters

- **Search works in both languages:** Type in Spanish or English
- **Sorting:** Sorted by current admin language
- **Bulk actions:** Select multiple items for batch operations

---

## Tips & Best Practices

### Content Guidelines

✅ **Do:**
- Write clear, professional descriptions
- Use proper HTML tags in Text Content
- Include relevant keywords
- Keep strain names in English
- Fill all required fields

❌ **Don't:**
- Don't translate strain names
- Don't translate terpene names
- Don't leave required fields empty
- Don't use excessive HTML formatting

### SEO Best Practices

- **Title:** 50-60 characters
- **Description:** 150-160 characters
- **Keywords:** 5-10 relevant terms, comma-separated
- **Alt Text:** Descriptive, 10-15 words

### Quality Checks

Before publishing:
- [ ] Both language versions filled
- [ ] No spelling errors
- [ ] HTML renders correctly
- [ ] Images have alt text
- [ ] Keywords relevant
- [ ] Preview on frontend
- [ ] Translation status is "Synced" (green badge)

### Smart Editing Tips

**💡 Best Practices:**
- Fix multiple typos at once, then check "Skip translation"
- HTML formatting changes don't need re-translation
- Minor edits can be done with checkbox checked

**⚠️ When NOT to use "Skip translation":**
- Never check it when adding NEW content
- Don't use for significant text changes
- Avoid if you changed product specifications

**🎯 Batch Editing:**
If editing multiple items with same type of change (e.g., fixing same typo across articles):
1. Fix all items one by one
2. Check "Skip translation" for each
3. Saves processing time

---

## Troubleshooting

**Problem:** Can't see language tabs
**Solution:** Model might not be registered for translation. Contact developer.

**Problem:** Translation badge shows "Failed"
**Solution:** Check admin error message. Use "Force retranslate" action to retry.

**Problem:** Content doesn't appear on frontend
**Solution:**
1. Check if item is marked as "active"
2. Clear browser cache
3. Check if correct language selected

**Problem:** Language switcher doesn't work
**Solution:** Check browser JavaScript console. Clear cache. Contact developer if persists.

---

## FAQ

**Q: Which language should I edit first?**
A: Always edit **English (EN)** first. AI will automatically translate to Spanish.

**Q: When should I check "Skip translation"?**
A: Check it when making minor edits (typos, formatting) that don't need re-translation.

**Q: What if I forget to check "Skip translation" for HTML changes?**
A: No problem! The system automatically detects HTML-only changes (h1→h2, bold→italic) and won't trigger re-translation.

**Q: Can I edit AI translations?**
A: Yes! Always review and edit AI translations for quality and accuracy. When editing the translated version, check "Skip translation" to avoid re-translating back.

**Q: What happens if I edit only one language?**
A: The other language version will show as "outdated". You can either let AI re-translate, or manually edit both versions and check "Skip translation".

**Q: How long does AI translation take?**
A: Approximately 30-60 seconds per item. The page will save immediately; translation happens in the background.

**Q: Will translation work if I save multiple times quickly?**
A: Yes, but only the last save will trigger translation if content changed. Previous translations may be skipped.

**Q: Does "Skip translation" affect both languages?**
A: It prevents re-translation of the OTHER language. Your edited language is always saved.

**Q: Can I undo a translation?**
A: Yes, just edit the field manually in the ES tab and save. Check "Skip translation" to keep your manual edit.

**Q: What happens if translation fails?**
A: Status badge shows "Failed". You can manually translate, or select item and use "Force retranslate" action.

---

## Support

**Need help?**
- Check this guide first
- Contact development team
- Technical details: See `AI_TRANSLATION_SETUP.md`

**Report issues:**
- Translation quality problems
- Missing translations
- Frontend display errors
- Admin interface bugs

---

## UI Translation System (Django i18n)

**Note:** This section covers **interface translations** (buttons, labels, static text), which is separate from **content translations** (Strains, Articles) described above.

### What is UI Translation?

The UI translation system translates static interface elements:
- Navigation menu ("Variedades" → "Strains")
- Buttons ("Ver más" → "See more")
- Labels ("Categoría" → "Category")
- Static page text and headings
- Filter options ("Sin THC" → "No THC")

### For Developers: Local Development Workflow

When adding new templates or modifying static text:

#### 1. **Wrap text in translation tags**

```django
{% load i18n %}
<h1>{% trans "Nuevo título" %}</h1>
<button>{% trans "Guardar" %}</button>
```

For forms (Python code):
```python
from django.utils.translation import gettext_lazy as _

choices=[
    ('option1', _('Opción 1')),
]
```

#### 2. **Extract translatable strings**

```bash
# Run inside Docker container
docker-compose exec web python manage.py makemessages -l en
```

This updates `locale/en/LC_MESSAGES/django.po` with new strings.

#### 3. **Add English translations**

Edit `locale/en/LC_MESSAGES/django.po`:
```
#: templates/new_page.html:5
msgid "Nuevo título"
msgstr "New Title"  # ← Add translation here
```

#### 4. **Compile translations**

```bash
# Compile .po → .mo binary files
docker-compose exec web python manage.py compilemessages
```

#### 5. **Restart server to apply changes**

```bash
docker-compose restart web
```

### Quick Command Reference

```bash
# Complete workflow
docker-compose exec web python manage.py makemessages -l en
# Edit locale/en/LC_MESSAGES/django.po manually
docker-compose exec web python manage.py compilemessages
docker-compose restart web
```

### Production Deployment (Automatic)

**How it works on production:**

1. Developer commits changes:
   - Updated templates with `{% trans %}` tags
   - Updated `locale/en/LC_MESSAGES/django.po` with translations
   - `.mo` files are **NOT** committed (in `.gitignore`)

2. Push to `master` branch triggers GitHub Actions workflow

3. Deployment process:
   ```
   ├─ SSH to EC2 server
   ├─ Stop Docker containers
   ├─ Pull latest code (includes .po files)
   ├─ Start Docker containers
   └─ Compile translations automatically
      └─ docker-compose exec -T web python manage.py compilemessages
   ```

4. `.mo` files are generated on server filesystem
5. Django loads compiled translations automatically

**Key Points:**
- ✅ **Commit:** `.po` files (source translations)
- ❌ **Don't commit:** `.mo` files (binary, auto-generated)
- 🤖 **Automatic:** Compilation happens during deployment
- 🔄 **No manual steps:** Translations compile on every deployment

### File Structure

```
locale/
└── en/
    └── LC_MESSAGES/
        ├── django.po    ✅ Committed (source translations)
        └── django.mo    ❌ Ignored (.gitignore, auto-generated)
```

### Terminology Guidelines

**Use "cannabis" not "marijuana":**
- ✅ "Cannabis Strains Guide"
- ❌ "Marijuana Strains Guide"

**Reason:** "Cannabis" is more professional, scientific, and legally appropriate.

### Troubleshooting

**Problem:** Translations don't appear on frontend
**Solution:**
1. Check if `compilemessages` was run
2. Restart Django server
3. Clear browser cache
4. Verify language code in URL (`/en/...`)

**Problem:** New strings not in django.po
**Solution:**
1. Ensure `{% load i18n %}` at top of template
2. Check `{% trans %}` tag syntax
3. Run `makemessages` again

**Problem:** Permission denied editing django.po
**Solution:**
- File owned by Docker container user
- Use `docker-compose exec web` commands instead of direct editing

**Problem:** Changes not visible after compilemessages
**Solution:** Must restart Django server for changes to take effect

---

## What's New

### Version 1.2 (2025-10-17)
- ✅ Added "Skip translation" checkbox for minor edits
- ✅ Automatic detection of HTML-only changes (no re-translation)
- ✅ Automatic AI translation (EN↔ES) via OpenAI API
- ✅ New workflow examples and decision charts
- ✅ Expanded FAQ section
- ✅ Removed AWS references (not used in current implementation)

### Version 1.1 (2025-10-15)
- Initial Django i18n setup
- UI translation workflow

---

**Last Updated:** 2025-10-17
**Version:** 1.2
**For technical setup:** See `AI_TRANSLATION_SETUP.md`
