from django.db import migrations


def mark_existing_emails_verified(apps, schema_editor):
    """Backfill allauth EmailAddress rows for users created before email verification was mandatory.

    Without this, switching ACCOUNT_EMAIL_VERIFICATION to 'mandatory' would lock out every
    existing user since allauth blocks login when no verified EmailAddress exists.
    """
    User = apps.get_model('users', 'CustomUser')
    EmailAddress = apps.get_model('account', 'EmailAddress')

    for user in User.objects.exclude(email='').iterator():
        existing = EmailAddress.objects.filter(user=user, email__iexact=user.email).first()
        if existing:
            if not existing.verified or not existing.primary:
                existing.verified = True
                existing.primary = True
                existing.save(update_fields=['verified', 'primary'])
            continue

        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True,
            primary=not EmailAddress.objects.filter(user=user, primary=True).exists(),
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_customuser_display_name'),
        ('account', '0009_emailaddress_unique_primary_email'),
    ]

    operations = [
        migrations.RunPython(mark_existing_emails_verified, noop),
    ]
