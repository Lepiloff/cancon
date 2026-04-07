from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.strains.factories import StrainFactory
from apps.strains.models import FavoriteStrain, StrainComment

from .models import ConsumptionNote


class UsersManagersTests(TestCase):

    def test_create_user(self):
        User = get_user_model()
        user = User.objects.create_user(email="normal@user.com", password="foo")
        self.assertEqual(user.email, "normal@user.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        try:
            # username is None for the AbstractUser option
            # username does not exist for the AbstractBaseUser option
            self.assertIsNone(user.username)
        except AttributeError:
            pass
        with self.assertRaises(TypeError):
            User.objects.create_user()
        with self.assertRaises(TypeError):
            User.objects.create_user(email="")
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="foo")

    def test_create_superuser(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser(email="super@user.com", password="foo")
        self.assertEqual(admin_user.email, "super@user.com")
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        try:
            # username is None for the AbstractUser option
            # username does not exist for the AbstractBaseUser option
            self.assertIsNone(admin_user.username)
        except AttributeError:
            pass
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="super@user.com", password="foo", is_superuser=False)

    def test_get_public_display_name_prefers_display_name(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="normal@user.com",
            password="foo",
            display_name="Juan",
        )

        self.assertEqual(user.get_display_name(), "Juan")
        self.assertEqual(user.get_public_display_name(), "Juan")

    def test_get_public_display_name_obfuscates_email_when_missing(self):
        User = get_user_model()
        user = User.objects.create_user(email="normaluser@user.com", password="foo")

        self.assertEqual(user.get_display_name(), "normaluser")
        self.assertEqual(user.get_public_display_name(), "no***r")


class DashboardViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            email="dashboard@example.com",
            password="foo12345",
        )
        self.strain = StrainFactory.create(active=True)
        FavoriteStrain.objects.create(user=self.user, strain=self.strain)
        StrainComment.objects.create(
            user=self.user,
            strain=self.strain,
            pros="Calming",
            cons="Dry mouth",
            reaction="thumbs_up",
            status="approved",
        )
        ConsumptionNote.objects.create(
            user=self.user,
            strain=self.strain,
            strain_name_text=self.strain.name,
            date=timezone.localdate(),
            notes="Private note",
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 302)

    def test_dashboard_shows_counts_for_authenticated_user(self):
        self.client.login(email="dashboard@example.com", password="foo12345")

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["favorite_count"], 1)
        self.assertEqual(response.context["comment_count"], 1)
        self.assertEqual(response.context["note_count"], 1)
        self.assertEqual(response.context["dashboard_section"], "overview")
        self.assertContains(response, "noindex, nofollow")

    def test_dashboard_journal_renders_autocomplete_context(self):
        self.client.login(email="dashboard@example.com", password="foo12345")

        response = self.client.get(reverse("dashboard_journal"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard_section"], "journal")
        self.assertIn("strain_autocomplete_url", response.context)
        self.assertContains(response, "data-strain-autocomplete-url")


class ConsumptionNoteViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            email="journal@example.com",
            password="foo12345",
        )
        self.other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="foo12345",
        )
        self.strain = StrainFactory.create(active=True)
        self.other_note = ConsumptionNote.objects.create(
            user=self.other_user,
            strain=self.strain,
            strain_name_text=self.strain.name,
            date=timezone.localdate(),
        )

    def test_journal_create_creates_note(self):
        self.client.login(email="journal@example.com", password="foo12345")

        response = self.client.post(
            reverse("journal_create"),
            {
                "strain_name_text": "Manual strain",
                "date": timezone.localdate().isoformat(),
                "notes": "Relaxed and focused",
                "method": "vape",
                "mood_before": 2,
                "mood_after": 4,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ConsumptionNote.objects.filter(
                user=self.user,
                strain_name_text="Manual strain",
            ).exists()
        )

    def test_journal_json_returns_owner_note(self):
        note = ConsumptionNote.objects.create(
            user=self.user,
            strain=self.strain,
            strain_name_text=self.strain.name,
            date=timezone.localdate(),
            notes="Private note",
        )
        self.client.login(email="journal@example.com", password="foo12345")

        response = self.client.get(reverse("journal_json", args=[note.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["note"]["id"], note.id)

    def test_journal_json_rejects_other_user_note(self):
        self.client.login(email="journal@example.com", password="foo12345")

        response = self.client.get(reverse("journal_json", args=[self.other_note.id]))

        self.assertEqual(response.status_code, 404)

    def test_journal_update_rejects_other_user_note(self):
        self.client.login(email="journal@example.com", password="foo12345")

        response = self.client.post(
            reverse("journal_update", args=[self.other_note.id]),
            {
                "strain_name_text": "Updated",
                "date": timezone.localdate().isoformat(),
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_journal_delete_rejects_other_user_note(self):
        self.client.login(email="journal@example.com", password="foo12345")

        response = self.client.post(reverse("journal_delete", args=[self.other_note.id]))

        self.assertEqual(response.status_code, 404)
