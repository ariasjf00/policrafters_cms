from django.core.exceptions import ValidationError
from django.test import TestCase
from wagtail.models import Locale

from shared_cms.models import DirectContactBlock


class DirectContactBlockValidationTests(TestCase):
    def test_allows_only_one_block_per_locale(self):
        default_locale = Locale.get_default()

        DirectContactBlock.objects.create(
            locale=default_locale,
            title="Default EN",
            contact_heading="Heading",
            contact_cta="CTA",
        )

        duplicate = DirectContactBlock(
            locale=default_locale,
            title="Duplicate EN",
            contact_heading="Other heading",
            contact_cta="Other CTA",
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_allows_one_block_for_different_locales(self):
        en_locale = Locale.get_default()
        es_locale, _ = Locale.objects.get_or_create(language_code="es")

        DirectContactBlock.objects.create(
            locale=en_locale,
            title="English block",
            contact_heading="Heading",
            contact_cta="CTA",
        )

        spanish_block = DirectContactBlock(
            locale=es_locale,
            title="Spanish block",
            contact_heading="Titulo",
            contact_cta="Accion",
        )

        spanish_block.full_clean()
