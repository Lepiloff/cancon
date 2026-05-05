from django.db import migrations
from django.db.models import Q


ACCENT_FIXES = (
    ('Inflamacion', 'Inflamación'),
    ('Presion ocular', 'Presión ocular'),
)


def _field_names(model):
    return {field.name for field in model._meta.get_fields()}


def _find_target(HelpsWith, target_name, exclude_pk=None):
    lookup = Q(name__iexact=target_name)
    field_names = _field_names(HelpsWith)
    if 'name_en' in field_names:
        lookup |= Q(name_en__iexact=target_name)
    if 'name_es' in field_names:
        lookup |= Q(name_es__iexact=target_name)

    queryset = HelpsWith.objects.filter(lookup).order_by('id')
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.first()


def _merge_links(Through, source, target):
    strain_ids = Through.objects.filter(
        helpswith_id=source.pk,
    ).values_list('strain_id', flat=True)

    for strain_id in strain_ids.iterator():
        Through.objects.get_or_create(
            strain_id=strain_id,
            helpswith_id=target.pk,
        )

    Through.objects.filter(helpswith_id=source.pk).delete()


def fix_helps_with_accents(apps, schema_editor):
    Strain = apps.get_model('strains', 'Strain')
    HelpsWith = apps.get_model('strains', 'HelpsWith')
    Through = Strain.helps_with.through
    field_names = _field_names(HelpsWith)

    for source_name, target_name in ACCENT_FIXES:
        sources = list(HelpsWith.objects.filter(name__iexact=source_name).order_by('id'))

        for source in sources:
            target = _find_target(HelpsWith, target_name, exclude_pk=source.pk)
            if target:
                _merge_links(Through, source, target)
                source.delete()
                continue

            update_fields = ['name']
            source.name = target_name
            if 'name_es' in field_names:
                source.name_es = target_name
                update_fields.append('name_es')
            if (
                'name_en' in field_names
                and (
                    not source.name_en
                    or source.name_en.casefold() == source_name.casefold()
                )
            ):
                source.name_en = target_name
                update_fields.append('name_en')
            source.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ('strains', '0024_merge_negative_anxiety'),
    ]

    operations = [
        migrations.RunPython(fix_helps_with_accents, migrations.RunPython.noop),
    ]
