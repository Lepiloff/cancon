from django.db import migrations
from django.db.models import Q


TERPENE_MERGES = (
    {
        'source_names': ('Cariofileno (picante)',),
        'target_name': 'Caryophyllene',
        'target_name_es': 'Cariofileno',
    },
    {
        'source_names': ('Humuleno (terroso)',),
        'target_name': 'Humulene',
        'target_name_es': 'Humuleno',
    },
    {
        'source_names': ('Limoneno (citrus)', 'Limoneno (cítrico)'),
        'target_name': 'Limonene',
        'target_name_es': 'Limoneno',
    },
    {
        'source_names': ('Linalool (floral)',),
        'target_name': 'Linalool',
        'target_name_es': 'Linalool',
    },
    {
        'source_names': ('Mirceno (herbal)',),
        'target_name': 'Myrcene',
        'target_name_es': 'Mirceno',
    },
    {
        'source_names': ('Ocimeno (floral)', 'Ocimeno (dulce)'),
        'target_name': 'Ocimene',
        'target_name_es': 'Ocimeno',
    },
    {
        'source_names': ('Pineno (woody)', 'Pineno (amaderado)'),
        'target_name': 'Pinene',
        'target_name_es': 'Pineno',
    },
    {
        'source_names': ('Terpinoleno (floral)',),
        'target_name': 'Terpinolene',
        'target_name_es': 'Terpinoleno',
    },
)


def _field_names(model):
    return {field.name for field in model._meta.get_fields()}


def _find_terpene(Terpene, name):
    field_names = _field_names(Terpene)
    lookup = Q(name__iexact=name)
    if 'name_en' in field_names:
        lookup |= Q(name_en__iexact=name)
    if 'name_es' in field_names:
        lookup |= Q(name_es__iexact=name)
    return Terpene.objects.filter(lookup).order_by('id').first()


def _set_if_field(obj, field_names, field_name, value, update_fields):
    if field_name in field_names and getattr(obj, field_name, None) != value:
        setattr(obj, field_name, value)
        update_fields.append(field_name)


def _copy_if_target_blank(source, target, field_names, field_name, update_fields):
    if field_name not in field_names:
        return
    source_value = getattr(source, field_name, None)
    target_value = getattr(target, field_name, None)
    if source_value and not target_value:
        setattr(target, field_name, source_value)
        update_fields.append(field_name)


def _normalize_target_fields(target, target_name, target_name_es):
    field_names = _field_names(target.__class__)
    update_fields = []
    _set_if_field(target, field_names, 'name', target_name, update_fields)
    _set_if_field(target, field_names, 'name_en', target_name, update_fields)
    _set_if_field(target, field_names, 'name_es', target_name_es, update_fields)
    if update_fields:
        target.save(update_fields=update_fields)


def _preserve_source_content(source, target):
    field_names = _field_names(target.__class__)
    update_fields = []
    for field_name in ('description', 'description_en', 'description_es'):
        _copy_if_target_blank(source, target, field_names, field_name, update_fields)

    if update_fields:
        target.save(update_fields=update_fields)


def _merge_other_terpene_links(Through, source, target):
    strain_ids = Through.objects.filter(
        terpene_id=source.pk,
    ).values_list('strain_id', flat=True)

    for strain_id in strain_ids.iterator():
        Through.objects.get_or_create(
            strain_id=strain_id,
            terpene_id=target.pk,
        )

    Through.objects.filter(terpene_id=source.pk).delete()


def consolidate_terpene_variants(apps, schema_editor):
    Strain = apps.get_model('strains', 'Strain')
    Terpene = apps.get_model('strains', 'Terpene')
    Through = Strain.other_terpenes.through

    for merge in TERPENE_MERGES:
        target_name = merge['target_name']
        target_name_es = merge['target_name_es']
        target = _find_terpene(Terpene, target_name)

        for source_name in merge['source_names']:
            source = _find_terpene(Terpene, source_name)
            if not source:
                continue

            if not target:
                target = source
                _normalize_target_fields(target, target_name, target_name_es)
                continue

            if source.pk == target.pk:
                _normalize_target_fields(target, target_name, target_name_es)
                continue

            _preserve_source_content(source, target)
            Strain.objects.filter(dominant_terpene_id=source.pk).update(
                dominant_terpene_id=target.pk,
            )
            _merge_other_terpene_links(Through, source, target)
            source.delete()

        if target:
            _normalize_target_fields(target, target_name, target_name_es)


class Migration(migrations.Migration):

    dependencies = [
        ('strains', '0025_fix_helps_with_accents'),
    ]

    operations = [
        migrations.RunPython(consolidate_terpene_variants, migrations.RunPython.noop),
    ]
