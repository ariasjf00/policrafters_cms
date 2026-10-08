from django.test import RequestFactory

from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase

from terms_cms.models import TermItem, TermsPage


class TermsApiTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )

        self.page = TermsPage(
            title="Terms & Conditions",
            intro_heading="Terms and Conditions",
            intro_body="Please review these terms before using the website.",
            search_description="Terms page",
        )
        root_page.add_child(instance=self.page)

        TermItem.objects.create(
            page=self.page,
            key="scope-and-acceptance",
            title="Scope and Acceptance",
            body="By using this website, you accept these terms and conditions.",
        )
        TermItem.objects.create(
            page=self.page,
            key="intellectual-property",
            title="Intellectual Property",
            body="All content is protected by applicable copyright laws.",
            sort_order=1,
        )

    def test_terms_api_defaults_to_english_when_lang_missing(self):
        response = self.client.get("/api/terms-page")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["locale"], "en")

    def test_terms_api_defaults_to_english_when_lang_invalid(self):
        response = self.client.get("/api/terms-page?lang=pt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["locale"], "en")

    def test_terms_api_returns_contract_shape(self):
        response = self.client.get("/api/terms-page?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "terms.TermsPage")
        self.assertIn("meta", data)
        self.assertIn("fields", data)
        self.assertIn("terms", data["fields"])
        self.assertEqual(data["fields"]["intro_heading"], "Terms and Conditions")
        self.assertEqual(len(data["fields"]["terms"]), 2)
        keys = [term["key"] for term in data["fields"]["terms"]]
        self.assertIn("scope-and-acceptance", keys)
        self.assertIn("intellectual-property", keys)


class TermsPageRenderTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )
        self.page = TermsPage(title="Terms & Conditions", intro_heading="Terms and Conditions")
        root_page.add_child(instance=self.page)

    def test_terms_page_is_renderable(self):
        self.assertPageIsRenderable(self.page)

    def test_terms_page_preview_renders_astro_iframe_and_payload(self):
        request = RequestFactory().get("/admin/")
        response = self.page.serve_preview(request, mode_name="default")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("/terms-and-conditions/?lang=en", content)
        self.assertIn('"type": "terms.TermsPage"', content)
