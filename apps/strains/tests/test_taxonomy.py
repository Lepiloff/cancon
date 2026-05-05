import importlib
import json
from unittest.mock import Mock

import pytest
from django.apps import apps as django_apps
from django.core.management import call_command
from django.utils.translation import override

from apps.strains.leafly_import import StrainPersister
from apps.strains.models import (
    Article,
    ArticleCategory,
    Flavor,
    Feeling,
    HelpsWith,
    Negative,
    Strain,
    Terpene,
)
from apps.strains.taxonomy import get_or_create_taxonomy_term
from apps.strains.views import _find_terpenes_for_article, _get_terpene_article_slugs


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
def test_get_or_create_taxonomy_term_canonicalizes_helps_with_accents():
    existing = HelpsWith.objects.create(
        name='Inflamación',
        name_en='Inflamación',
        name_es='Inflamación',
    )

    term, created = get_or_create_taxonomy_term(HelpsWith, 'Inflamacion')

    assert term == existing
    assert created is False
    assert HelpsWith.objects.count() == 1


@pytest.mark.django_db
def test_leafly_taxonomy_resolution_canonicalizes_helps_with_accents():
    existing = HelpsWith.objects.create(
        name='Inflamación',
        name_en='Inflamación',
        name_es='Inflamación',
    )
    translator = Mock()
    persister = StrainPersister(translator)

    resolved = persister._resolve_taxonomy(
        ['Inflamacion'],
        HelpsWith,
        persister.helps_with_cache,
    )

    assert resolved == [existing]
    translator.translate_terms.assert_not_called()


@pytest.mark.django_db
def test_get_or_create_taxonomy_term_canonicalizes_terpene_aliases():
    existing = Terpene.objects.create(
        name='Myrcene',
        name_en='Myrcene',
        name_es='Mirceno',
    )

    term, created = get_or_create_taxonomy_term(Terpene, 'Mirceno (herbal)')

    assert term == existing
    assert created is False
    assert Terpene.objects.count() == 1


@pytest.mark.django_db
def test_terpene_article_matching_uses_english_names_for_spanish_variants():
    category = ArticleCategory.objects.create(name='Terpenes')
    article = Article.objects.create(
        title='Myrcene: properties',
        text_content='Terpene content.',
        description='Myrcene description',
        keywords='myrcene',
        slug='myrcene',
    )
    article.category.add(category)
    spanish_variant = Terpene.objects.create(
        name='Mirceno (herbal)',
        name_en='Myrcene (herbal)',
        name_es='Mirceno (herbal)',
    )
    pure_variant = Terpene.objects.create(
        name='Myrcene',
        name_en='Myrcene',
        name_es='Mirceno',
    )

    slugs = _get_terpene_article_slugs([spanish_variant, pure_variant])
    matches = _find_terpenes_for_article(article)

    assert slugs[spanish_variant.id] == 'myrcene'
    assert slugs[pure_variant.id] == 'myrcene'
    assert set(matches) == {spanish_variant, pure_variant}


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


@pytest.mark.django_db
def test_consolidate_terpene_variants_migration_moves_links_and_preserves_content():
    migration_module = importlib.import_module(
        'apps.strains.migrations.0026_consolidate_terpene_variants'
    )

    with override('en'):
        source = Terpene.objects.create(
            name='Mirceno (herbal)',
            name_en='Myrcene (herbal)',
            name_es='Mirceno (herbal)',
            description='Source description',
        )
        target = Terpene.objects.create(
            name='Myrcene',
            name_en='Myrcene',
            name_es='Myrcene',
            description='',
        )
        dominant_strain = Strain.objects.create(
            name='Dominant Terpene Strain',
            title='Dominant Terpene Strain',
            text_content='Content',
            description='Description',
            keywords='terpene',
            category='Hybrid',
            slug='dominant-terpene-strain',
            active=True,
            dominant_terpene=source,
        )
        other_strain = Strain.objects.create(
            name='Other Terpene Strain',
            title='Other Terpene Strain',
            text_content='Content',
            description='Description',
            keywords='terpene',
            category='Hybrid',
            slug='other-terpene-strain',
            active=True,
        )
        other_strain.other_terpenes.add(source, target)

        migration_module.consolidate_terpene_variants(django_apps, None)

        dominant_strain.refresh_from_db()
        other_strain.refresh_from_db()
        target.refresh_from_db()
        assert dominant_strain.dominant_terpene == target
        assert set(other_strain.other_terpenes.all()) == {target}
        assert other_strain.other_terpenes.count() == 1
        assert target.name == 'Myrcene'
        assert target.name_en == 'Myrcene'
        assert target.name_es == 'Mirceno'
        assert target.description == 'Source description'
        assert Terpene.objects.filter(name__iexact='Mirceno (herbal)').exists() is False
