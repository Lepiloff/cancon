from django.db import models
from django.db.models import Q


TRANSLATED_NAME_FIELDS = ('name', 'name_en', 'name_es')
TAXONOMY_NAME_ALIASES = {
    'strains.Negative': {
        'anxiety': 'Anxious',
        'ansiedad': 'Anxious',
    },
    'strains.HelpsWith': {
        'inflamacion': 'Inflamación',
        'presion ocular': 'Presión ocular',
    },
}


def normalize_taxonomy_name(name: str) -> str:
    return ' '.join(str(name).split())


def canonical_taxonomy_name(model: type[models.Model], name: str) -> str:
    model_key = f'{model._meta.app_label}.{model._meta.object_name}'
    aliases = TAXONOMY_NAME_ALIASES.get(model_key, {})
    return aliases.get(name.casefold(), name)


def _find_taxonomy_term(model: type[models.Model], name: str):
    model_fields = {field.name for field in model._meta.get_fields()}
    lookup = Q()
    for field_name in TRANSLATED_NAME_FIELDS:
        if field_name in model_fields:
            lookup |= Q(**{f'{field_name}__iexact': name})

    return model.objects.filter(lookup).first() if lookup else None


def get_or_create_taxonomy_term(model: type[models.Model], name: str):
    normalized_name = normalize_taxonomy_name(name)
    if not normalized_name:
        raise ValueError('Taxonomy name cannot be empty')

    canonical_name = canonical_taxonomy_name(model, normalized_name)
    existing = _find_taxonomy_term(model, canonical_name)
    if not existing and canonical_name != normalized_name:
        existing = _find_taxonomy_term(model, normalized_name)
    if existing:
        return existing, False

    return model.objects.create(name=canonical_name), True
