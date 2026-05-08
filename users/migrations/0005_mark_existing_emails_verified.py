from django.db import migrations


def backfill_email_addresses(User, EmailAddress):
    """Ensure every existing user has a verified EmailAddress matching User.email.

    Without this, switching ACCOUNT_EMAIL_VERIFICATION to 'mandatory' would lock
    out every existing user since allauth blocks login when no verified
    EmailAddress exists.

    Constraints we respect:
    - allauth enforces a unique primary EmailAddress per user; we never set a
      second `primary=True` and never flip an existing primary off.
    - We do not modify the `primary` flag on rows that already exist; only the
      `verified` flag, which is what unblocks login under mandatory verification.
    """
    for user in User.objects.exclude(email='').iterator():
        existing = EmailAddress.objects.filter(user=user, email__iexact=user.email).first()
        if existing:
            if not existing.verified:
                existing.verified = True
                existing.save(update_fields=['verified'])
            continue

        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True,
            primary=not EmailAddress.objects.filter(user=user, primary=True).exists(),
        )


def mark_existing_emails_verified(apps, schema_editor):
    User = apps.get_model('users', 'CustomUser')
    EmailAddress = apps.get_model('account', 'EmailAddress')
    backfill_email_addresses(User, EmailAddress)


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
