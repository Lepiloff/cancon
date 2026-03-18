"""
Populate Terpene name_en and name_es fields.

Current DB state: Terpene.name contains Spanish names like "Cariofileno (picante)".
This migration:
  - Copies current name → name_es
  - Maps Spanish name to English → name_en
"""

import re
from django.db import migrations


# Spanish → English terpene name mapping
TERPENE_NAME_MAP = {
    'Cariofileno': 'Caryophyllene',
    'Limoneno': 'Limonene',
    'Mirceno': 'Myrcene',
    'Terpinoleno': 'Terpinolene',
    'Pineno': 'Pinene',
    'Humuleno': 'Humulene',
    'Ocimeno': 'Ocimene',
    'Linalool': 'Linalool',
    'Bisabolol': 'Bisabolol',
    'Nerolidol': 'Nerolidol',
    'Valenceno': 'Valencene',
    'Geraniol': 'Geraniol',
    'Eucaliptol': 'Eucalyptol',
    'Felandreno': 'Phellandrene',
    'Borneol': 'Borneol',
    'Canfeno': 'Camphene',
    'Sabineno': 'Sabinene',
    'Pulegona': 'Pulegone',
    'Guaiol': 'Guaiol',
}

# Spanish → English descriptor mapping (the part in parentheses)
DESCRIPTOR_MAP = {
    'picante': 'spicy',
    'cítrico': 'citrus',
    'citrus': 'citrus',
    'herbal': 'herbal',
    'floral': 'floral',
    'woody': 'woody',
    'amaderado': 'woody',
    'dulce': 'sweet',
    'mentolado': 'menthol',
    'afrutado': 'fruity',
    'lúpulo': 'hoppy',
    'terroso': 'earthy',
}


def translate_to_english(spanish_name):
    """Convert Spanish terpene name like 'Cariofileno (picante)' → 'Caryophyllene (spicy)'."""
    # Parse: "TerpeneName (descriptor)" or just "TerpeneName"
    match = re.match(r'^(\S+)\s*\((.+)\)$', spanish_name.strip())

    if match:
        name_part = match.group(1)
        descriptor_part = match.group(2).strip()

        en_name = TERPENE_NAME_MAP.get(name_part, name_part)
        en_descriptor = DESCRIPTOR_MAP.get(descriptor_part.lower(), descriptor_part)
        return f'{en_name} ({en_descriptor})'
    else:
        # No descriptor, just map the name
        return TERPENE_NAME_MAP.get(spanish_name.strip(), spanish_name.strip())


def populate_terpene_translations(apps, schema_editor):
    Terpene = apps.get_model('strains', 'Terpene')

    for terpene in Terpene.objects.all():
        current_name = terpene.name or ''
        terpene.name_es = current_name
        terpene.name_en = translate_to_english(current_name)
        terpene.save(update_fields=['name_en', 'name_es'])


def reverse_migration(apps, schema_editor):
    Terpene = apps.get_model('strains', 'Terpene')
    Terpene.objects.all().update(name_en=None, name_es=None)


class Migration(migrations.Migration):

    dependencies = [
        ('strains', '0020_add_terpene_name_translations'),
    ]

    operations = [
        migrations.RunPython(populate_terpene_translations, reverse_migration),
    ]
