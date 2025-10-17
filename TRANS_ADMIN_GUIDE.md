# Admin Guide: Bilingual Content Management
**For Content Managers and Admins**

---

## Quick Reference

### Current Setup
✅ **Phase 1 Complete**: Manual bilingual editing via admin
⏳ **Phase 2 Pending**: Automatic AI translation (ES→EN, then EN→ES)

**What's Available Now:**
- Language tabs in admin forms (EN/ES)
- Language switcher on frontend (🇬🇧 EN / 🇪🇸 ES)
- Manual translation via admin tabs

**Current Data State:**
- Spanish content exists in most fields
- English fields are empty (awaiting Phase 2 translation)
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

### Force Retranslate (when AWS is configured)

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

### Current Workflow (Manual Translation)

1. **Create/Edit in Admin:**
   - Go to admin → Strains/Articles
   - Click on item or Add New

2. **Fill in Spanish (ES tab):**
   - Click ES tab
   - Fill all fields
   - Save

3. **Fill in English (EN tab):**
   - Click EN tab
   - Manually translate content
   - Save

4. **Verify on Frontend:**
   - Use language switcher to check both versions
   - Ensure content displays correctly

### Future Workflow (with AI Translation)

**Phase 2: Initial ES→EN translation**
- Developer runs bulk translation command
- All existing Spanish content translated to English

**Phase 3: Automatic EN→ES translation**
1. Admin adds content in **English (EN tab)**
2. Save
3. AI automatically translates to Spanish (~30 seconds)
4. Check translation quality in ES tab
5. Edit if needed

**Note:** After Phase 3, always add new content in **English first**.

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

---

## Troubleshooting

**Problem:** Can't see language tabs
**Solution:** Model might not be registered for translation. Contact developer.

**Problem:** Translation badge shows "Failed"
**Solution:** (After AWS setup) Check admin error message. Use "Force retranslate" action.

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
A: Currently, edit Spanish (ES) first since most content is in Spanish. After Phase 3 setup, always edit English (EN) first.

**Q: Do I need to translate manually?**
A: For now, yes. After Phase 3 AWS setup, AI will auto-translate EN→ES.

**Q: Can I edit AI translations?**
A: Yes! Always review and edit AI translations for quality and accuracy.

**Q: What happens if I edit only one language?**
A: The other language version will show as "pending" or "outdated". Frontend will show whichever version exists.

**Q: How long does AI translation take?**
A: (After Phase 3) Approximately 30-60 seconds per item.

**Q: Can I undo a translation?**
A: Yes, just edit the field manually and save.

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

**Last Updated:** 2025-10-15
**Version:** 1.1
**For technical setup:** See `AI_TRANSLATION_SETUP.md`
