import importlib
import json

import pytest
from django.apps import apps as django_apps
from django.core.management import call_command
from django.utils.translation import override

from apps.strains.models import Flavor, Feeling, Negative, Strain
from apps.strains.taxonomy import get_or_create_taxonomy_term


@pytest.mark.django_db
def test_get_or_create_taxonomy_term_reuses_case_insensitive_name():
    existing = Negative.objects.create(
        name='Anxious',
        name_en='Anxious',
        name_es='Ansioso',
    )

    term, created = get_or_create_taxonomy_term(Negative, '  anxious  ')

    assert term == existing
    assert created is False
    assert Negative.objects.count() == 1


@pytest.mark.django_db
def test_get_or_create_taxonomy_term_reuses_translated_name():
    existing = Negative.objects.create(
        name='Anxious',
        name_en='Anxious',
        name_es='Ansioso',
    )

    term, created = get_or_create_taxonomy_term(Negative, 'ansioso')

    assert term == existing
    assert created is False
    assert Negative.objects.count() == 1


@pytest.mark.django_db
def test_get_or_create_taxonomy_term_canonicalizes_negative_anxiety_alias():
    existing = Negative.objects.create(
        name='Anxious',
        name_en='Anxious',
        name_es='Ansioso',
    )

    term, created = get_or_create_taxonomy_term(Negative, 'Anxiety')

    assert term == existing
    assert created is False
    assert Negative.objects.count() == 1

    term, created = get_or_create_taxonomy_term(Negative, 'ansiedad')
    assert term == existing
    assert created is False
    assert Negative.objects.count() == 1


@pytest.mark.django_db
def test_import_strains_reuses_existing_taxonomy_terms_case_insensitively(tmp_path):
    feeling = Feeling.objects.create(name='Happy', name_en='Happy', name_es='Feliz')
    negative = Negative.objects.create(
        name='Anxious',
        name_en='Anxious',
        name_es='Ansioso',
    )
    flavor = Flavor.objects.create(name='sweet', name_en='sweet', name_es='Dulce')

    import_file = tmp_path / 'strains.json'
    import_file.write_text(json.dumps({
        'example': {
            'strain_name': 'Example Import Strain',
            'rating': '4.5',
            'category': 'Hybrid',
            'thc': '18.0',
            'text_content': 'Imported strain content.',
            'feelings': ['happy'],
            'negatives': ['Anxiety'],
            'flavors': ['sweet'],
            'img_url': '',
        },
    }))

    call_command('import_strains', str(import_file))

    strain = Strain.objects.get(name='Example Import Strain')
    assert list(strain.feelings.all()) == [feeling]
    assert list(strain.negatives.all()) == [negative]
    assert list(strain.flavors.all()) == [flavor]
    assert Feeling.objects.count() == 1
    assert Negative.objects.count() == 1
    assert Flavor.objects.count() == 1


@pytest.mark.django_db
def test_merge_negative_anxiety_migration_moves_links_and_deletes_duplicate():
    migration_module = importlib.import_module(
        'apps.strains.migrations.0024_merge_negative_anxiety'
    )

    with override('en'):
        anxious = Negative.objects.create(
            name='Anxious',
            name_en='Anxious',
            name_es='Ansioso',
        )
        anxiety = Negative.objects.create(
            name='Anxiety',
            name_en='Anxiety',
            name_es='Anxiety',
        )
        strain = Strain.objects.create(
            name='Migration Test Strain',
            title='Migration Test Strain',
            text_content='Content',
            description='Description',
            keywords='migration',
            category='Hybrid',
            slug='migration-test-strain',
            active=True,
        )
        strain.negatives.add(anxiety)

        migration_module.merge_negative_anxiety(django_apps, None)

        strain.refresh_from_db()
        anxious.refresh_from_db()
        assert list(strain.negatives.all()) == [anxious]
        assert Negative.objects.filter(name__iexact='Anxiety').exists() is False
        assert Negative.objects.filter(name__iexact='Anxious').count() == 1
