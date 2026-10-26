from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from wagtail.contrib.settings.registry import registry

from site_settings.models import SiteSettings


class SiteSettingsApiTests(TestCase):
    def test_empty_site_settings_returns_contract_shape_without_creating_record(self):
        response = self.client.get("/api/site-settings")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["type"], "site.SiteSettings")
        self.assertEqual(data["title"], "Site settings")
        self.assertEqual(data["locale"], "en")
        self.assertEqual(data["meta"], {"seo_title": "", "search_description": ""})
        self.assertEqual(
            data["fields"],
            {
                "legal_name": "",
                "phone": "",
                "email": None,
                "addresses": [],
                "opening_hours": [],
                "area_served": [],
                "license_number": "",
                "certifications": [],
                "social_links": [],
                "logo": {"url": "", "alt": ""},
            },
        )
        self.assertEqual(SiteSettings.objects.count(), 0)

    def test_site_settings_returns_language_specific_meta_and_company_data(self):
        SiteSettings.objects.create(
            legal_name="Confirmed company name",
            phone="Confirmed phone",
            email="info@example.com",
            addresses=[
                {
                    "street": "Confirmed street",
                    "city": "Confirmed city",
                    "region": "Confirmed region",
                    "postal_code": "Confirmed postal code",
                    "country": "Confirmed country",
                }
            ],
            opening_hours=["Mo-Fr 08:00-17:00"],
            area_served=["Confirmed area"],
            license_number="Confirmed license",
            certifications=[
                {
                    "name": "Confirmed certification",
                    "issuer": None,
                    "url": None,
                }
            ],
            social_links=["https://social.example.com/company"],
            seo_title_en="English SEO title",
            seo_title_es="Spanish SEO title",
            search_description_en="English SEO description",
            search_description_es="Spanish SEO description",
        )

        response = self.client.get("/api/site-settings?locale=es")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["locale"], "es")
        self.assertEqual(
            data["meta"],
            {
                "seo_title": "Spanish SEO title",
                "search_description": "Spanish SEO description",
            },
        )
        self.assertEqual(data["fields"]["legal_name"], "Confirmed company name")
        self.assertEqual(data["fields"]["phone"], "Confirmed phone")
        self.assertEqual(data["fields"]["email"], "info@example.com")
        self.assertEqual(data["fields"]["addresses"][0]["city"], "Confirmed city")
        self.assertEqual(
            data["fields"]["certifications"][0]["issuer"],
            None,
        )

    def test_site_settings_accepts_lang_alias_and_defaults_invalid_locale_to_english(self):
        SiteSettings.objects.create(
            seo_title_en="English SEO title",
            seo_title_es="Spanish SEO title",
        )

        response = self.client.get("/api/site-settings?locale=pt&lang=en")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["locale"], "en")
        self.assertEqual(response.json()["meta"]["seo_title"], "English SEO title")


class SiteSettingsValidationTests(TestCase):
    def test_is_registered_as_a_wagtail_setting(self):
        self.assertIn(SiteSettings, registry)
        self.assertEqual(
            reverse("wagtailsettings:edit", args=["site_settings", "sitesettings"]),
            "/admin/settings/site_settings/sitesettings/",
        )

    def test_rejects_malformed_structured_data(self):
        settings = SiteSettings(
            addresses=[{"street": "Only a street"}],
            opening_hours={"weekday": "business hours"},
        )

        with self.assertRaises(ValidationError) as context:
            settings.full_clean()

        self.assertIn("addresses", context.exception.message_dict)
        self.assertIn("opening_hours", context.exception.message_dict)
