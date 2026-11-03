from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from wagtail.models import Locale, Page, Site
from wagtail.images import get_image_model
from wagtail.images.forms import get_image_form

from shared_cms.api_utils import (
    build_absolute_asset_url,
    normalize_image_payload,
    normalize_supported_language,
    resolve_request_language,
    serialize_image_payload,
)
from shared_cms.forms import RequiredAltTextImageForm
from shared_cms.models import (
    BrandsHeaderBlock,
    DirectContactBlock,
    FooterBlock,
    FooterCommercialLink,
    FooterNavigationLink,
    FooterResidentialLink,
    FooterSocialLink,
)


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


class FooterApiTests(TestCase):
    def test_empty_footer_returns_contract_shape(self):
        response = self.client.get("/api/footer?locale=es")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "type": "site.Footer",
                "title": "",
                "locale": "es",
                "fields": {
                    "copy": {
                        "blurb_1": "",
                        "blurb_2": "",
                        "phone_label": "",
                        "residential_label": "",
                        "email_label": "",
                        "commercial_label": "",
                        "address_label": "",
                        "social_label": "",
                        "copyright_text": "",
                    },
                    "navigation_links": [],
                    "residential_links": [],
                    "commercial_links": [],
                    "social_links": [],
                },
            },
        )

    def test_footer_returns_ordered_localized_link_groups(self):
        english_locale = Locale.get_default()
        footer = FooterBlock.objects.create(
            locale=english_locale,
            title="English footer",
            blurb_1="Quality craftsmanship",
            blurb_2="Built for every space",
            phone_label="Call",
            residential_label="Residential",
            email_label="Email",
            commercial_label="Commercial",
            address_label="Address",
            social_label="Follow us",
            copyright_text="Copyright 2026 Policrafters",
        )
        FooterNavigationLink.objects.create(
            footer=footer,
            locale=english_locale,
            sort_order=1,
            key="about",
            label="About",
            href="/about",
            localized_path="/about",
        )
        FooterNavigationLink.objects.create(
            footer=footer,
            locale=english_locale,
            sort_order=0,
            key="home",
            label="Home",
            href="/",
        )
        FooterResidentialLink.objects.create(
            footer=footer,
            locale=english_locale,
            key="windows",
            label="Windows",
            href="/windows",
        )
        FooterCommercialLink.objects.create(
            footer=footer,
            locale=english_locale,
            key="doors",
            label="Doors",
            href="/doors",
        )
        FooterSocialLink.objects.create(
            footer=footer,
            locale=english_locale,
            key="instagram",
            label="Instagram",
            href="https://instagram.com/example",
            icon="instagram",
        )

        response = self.client.get("/api/footer?locale=es")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["locale"], "en")
        self.assertEqual(data["title"], "English footer")
        self.assertEqual(
            data["fields"]["copy"],
            {
                "blurb_1": "Quality craftsmanship",
                "blurb_2": "Built for every space",
                "phone_label": "Call",
                "residential_label": "Residential",
                "email_label": "Email",
                "commercial_label": "Commercial",
                "address_label": "Address",
                "social_label": "Follow us",
                "copyright_text": "Copyright 2026 Policrafters",
            },
        )
        self.assertEqual(
            [link["key"] for link in data["fields"]["navigation_links"]],
            ["home", "about"],
        )
        self.assertEqual(
            data["fields"]["navigation_links"][0]["localizedPath"],
            "",
        )
        self.assertEqual(data["fields"]["residential_links"][0]["key"], "windows")
        self.assertEqual(data["fields"]["commercial_links"][0]["key"], "doors")
        self.assertEqual(
            data["fields"]["social_links"][0],
            {
                "key": "instagram",
                "label": "Instagram",
                "href": "https://instagram.com/example",
                "localizedPath": "",
                "icon": "instagram",
            },
        )

    def test_footer_allows_only_one_block_per_locale(self):
        english_locale = Locale.get_default()
        FooterBlock.objects.create(locale=english_locale, title="First footer")

        duplicate = FooterBlock(locale=english_locale, title="Duplicate footer")

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_footer_returns_requested_locale_when_translation_exists(self):
        spanish_locale, _ = Locale.objects.get_or_create(language_code="es")
        footer = FooterBlock.objects.create(
            locale=spanish_locale,
            title="Pie de página",
        )
        FooterNavigationLink.objects.create(
            footer=footer,
            locale=spanish_locale,
            key="inicio",
            label="Inicio",
            href="/",
        )

        response = self.client.get("/api/footer?locale=es")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["locale"], "es")
        self.assertEqual(data["title"], "Pie de página")
        self.assertEqual(data["fields"]["navigation_links"][0]["label"], "Inicio")


class ImagePayloadTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.media_settings = override_settings(
            MEDIA_ROOT=self.media_directory.name,
            WAGTAILADMIN_BASE_URL="https://cms.policrafters.com",
        )
        self.media_settings.enable()
        self.addCleanup(self.media_settings.disable)

    def _create_image(self):
        buffer = BytesIO()
        Image.new("RGB", (2000, 1200), color="white").save(buffer, format="PNG")
        return get_image_model().objects.create(
            title="Image title",
            description="  Descriptive   alternative text  ",
            file=SimpleUploadedFile(
                "seo-image.png",
                buffer.getvalue(),
                content_type="image/png",
            ),
        )

    def test_serializes_source_dimensions_alt_and_webp_renditions(self):
        request = RequestFactory().get("/api/home")
        image = self._create_image()

        payload = serialize_image_payload(image, request)

        self.assertEqual(payload["alt"], "Descriptive alternative text")
        self.assertEqual(payload["width"], 2000)
        self.assertEqual(payload["height"], 1200)
        self.assertTrue(payload["url"].startswith("https://cms.policrafters.com/media/"))
        self.assertEqual(set(payload["renditions"]), {"800", "1600"})
        self.assertTrue(all(url.endswith(".webp") for url in payload["renditions"].values()))

    def test_normalizes_extended_image_payloads_from_legacy_json(self):
        request = RequestFactory().get("/api/home")

        payload = normalize_image_payload(
            {
                "url": "/media/images/source.png",
                "alt": "  Legacy   image ",
                "width": 1200,
                "height": 800,
                "renditions": {"800": "/media/images/source-800.webp"},
            },
            request,
        )

        self.assertEqual(payload["alt"], "Legacy image")
        self.assertEqual(payload["width"], 1200)
        self.assertEqual(payload["height"], 800)
        self.assertEqual(
            payload["renditions"]["800"],
            "https://cms.policrafters.com/media/images/source-800.webp",
        )

    def test_missing_image_keeps_legacy_url_and_alt_shape(self):
        self.assertEqual(
            serialize_image_payload(None, alt_text="Fallback text"),
            {"url": "", "alt": "Fallback text"},
        )

    def test_wagtail_image_form_requires_alt_text(self):
        image_form = get_image_form(get_image_model())
        form = image_form(
            data={
                "title": "Image title",
                "description": "",
                "collection": "",
            }
        )

        self.assertIsInstance(form, RequiredAltTextImageForm)
        self.assertTrue(form.fields["description"].required)
        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)
