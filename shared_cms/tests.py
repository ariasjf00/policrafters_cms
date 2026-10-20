from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase, override_settings
from wagtail.models import Locale, Page, Site

from shared_cms.api_utils import build_absolute_asset_url, normalize_supported_language, resolve_request_language
from shared_cms.models import BrandsHeaderBlock, DirectContactBlock


class LocaleResolutionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_normalize_supported_language(self):
        self.assertEqual(normalize_supported_language("es-MX"), "es")
        self.assertEqual(normalize_supported_language("EN-us"), "en")
        self.assertIsNone(normalize_supported_language("pt"))
        self.assertIsNone(normalize_supported_language(None))

    def test_locale_query_param_has_priority_over_lang(self):
        request = self.factory.get("/api/home?lang=es&locale=en")
        self.assertEqual(resolve_request_language(request), "en")

    def test_locale_query_param_supports_regional_values(self):
        request = self.factory.get("/api/home?lang=en&locale=es-419")
        self.assertEqual(resolve_request_language(request), "es")

    def test_falls_back_to_lang_when_locale_is_missing_or_invalid(self):
        missing_locale_request = self.factory.get("/api/home?lang=es")
        self.assertEqual(resolve_request_language(missing_locale_request), "es")

        invalid_locale_request = self.factory.get("/api/home?locale=pt&lang=en")
        self.assertEqual(resolve_request_language(invalid_locale_request), "en")

    def test_defaults_to_english_when_no_supported_param_is_present(self):
        request = self.factory.get("/api/home?locale=pt&lang=fr")
        self.assertEqual(resolve_request_language(request), "en")

    @override_settings(WAGTAILADMIN_BASE_URL="https://cms.policrafters.com")
    def test_build_absolute_asset_url_uses_wagtail_admin_base_url(self):
        request = self.factory.get("/api/home")
        self.assertEqual(
            build_absolute_asset_url(request, "/media/sample.png"),
            "https://cms.policrafters.com/media/sample.png",
        )

    @override_settings(WAGTAILADMIN_BASE_URL="http://example.com")
    def test_build_absolute_asset_url_uses_non_testsite_default_site_when_available(self):
        request = self.factory.get("/api/home")
        self.assertEqual(
            build_absolute_asset_url(request, "/media/sample.png"),
            "http://localhost/media/sample.png",
        )

    @override_settings(WAGTAILADMIN_BASE_URL="http://localhost:8000")
    def test_build_absolute_asset_url_ignores_astro_preview_host(self):
        request = self.factory.get("/api/home", HTTP_HOST="localhost:4321")
        self.assertEqual(
            build_absolute_asset_url(request, "/media/sample.png"),
            "http://localhost:8000/media/sample.png",
        )

    @override_settings(WAGTAILADMIN_BASE_URL="http://example.com")
    def test_build_absolute_asset_url_falls_back_to_default_site_hostname(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            is_default_site=True,
            defaults={"hostname": "cms.local", "root_page": root_page},
        )
        request = self.factory.get("/api/home")
        self.assertEqual(
            build_absolute_asset_url(request, "/media/sample.png"),
            "http://cms.local/media/sample.png",
        )


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

    def test_duplicate_default_locale_detected_without_explicit_locale(self):
        default_locale = Locale.get_default()

        DirectContactBlock.objects.create(
            locale=default_locale,
            title="Default EN",
            contact_heading="Heading",
            contact_cta="CTA",
        )

        duplicate = DirectContactBlock(
            title="Implicit locale duplicate",
            contact_heading="Other heading",
            contact_cta="Other CTA",
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()


class BrandsHeaderBlockValidationTests(TestCase):
    def test_allows_only_one_block_per_locale(self):
        default_locale = Locale.get_default()

        BrandsHeaderBlock.objects.create(
            locale=default_locale,
            title="Default EN Brands",
        )

        duplicate = BrandsHeaderBlock(
            locale=default_locale,
            title="Duplicate EN Brands",
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_allows_one_block_for_different_locales(self):
        en_locale = Locale.get_default()
        es_locale, _ = Locale.objects.get_or_create(language_code="es")

        BrandsHeaderBlock.objects.create(
            locale=en_locale,
            title="English brands",
        )

        spanish_block = BrandsHeaderBlock(
            locale=es_locale,
            title="Spanish brands",
        )

        spanish_block.full_clean()

    def test_duplicate_default_locale_detected_without_explicit_locale(self):
        default_locale = Locale.get_default()

        BrandsHeaderBlock.objects.create(
            locale=default_locale,
            title="Default EN Brands",
        )

        duplicate = BrandsHeaderBlock(
            title="Implicit locale duplicate",
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()
