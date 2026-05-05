from django.db import migrations


def _field_names(model):
    return {field.name for field in model._meta.get_fields()}


def _set_if_field(obj, field_names, field_name, value, update_fields):
    if field_name in field_names:
        setattr(obj, field_name, value)
        update_fields.append(field_name)


def merge_negative_anxiety(apps, schema_editor):
    Strain = apps.get_model('strains', 'Strain')
    Negative = apps.get_model('strains', 'Negative')
    Through = Strain.negatives.through

    anxious_rows = list(Negative.objects.filter(name__iexact='Anxious').order_by('id'))
    anxiety_rows = list(Negative.objects.filter(name__iexact='Anxiety').order_by('id'))

    if anxious_rows:
        target = anxious_rows[0]
        sources = [row for row in anxious_rows[1:] + anxiety_rows if row.pk != target.pk]
    elif anxiety_rows:
        target = anxiety_rows[0]
        sources = [row for row in anxiety_rows[1:] if row.pk != target.pk]
    else:
        return

    for source in sources:
        strain_ids = Through.objects.filter(
            negative_id=source.pk,
        ).values_list('strain_id', flat=True)

        for strain_id in strain_ids.iterator():
            Through.objects.get_or_create(
                strain_id=strain_id,
                negative_id=target.pk,
            )

        Through.objects.filter(negative_id=source.pk).delete()
        source.delete()

    field_names = _field_names(Negative)
    update_fields = []
    _set_if_field(target, field_names, 'name', 'Anxious', update_fields)
    _set_if_field(target, field_names, 'name_en', 'Anxious', update_fields)
    _set_if_field(target, field_names, 'name_es', 'Ansioso', update_fields)
    if update_fields:
        target.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ('strains', '0023_straincomment'),
    ]

    operations = [
        migrations.RunPython(merge_negative_anxiety, migrations.RunPython.noop),
    ]
