from catalogs_cms.models import CatalogFilterCategory, CatalogIndexItem, CatalogIndexPage

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from wagtail.documents import get_document_model
from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase


class CatalogsApiTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )

        self.catalog_page = CatalogIndexPage(
            title="Catalogs",
            catalogs_eyebrow="Our Catalogs",
            catalogs_heading="EXPLORE OUR COLLECTIONS AND SOLUTIONS",
            catalogs_prev_aria="Previous",
            catalogs_next_aria="Next",
            catalogs_dot_aria="Go to page",
            filter_heading="Filter by",
            filter_all_label="All catalogs",
            empty_state_text="No catalogs found.",
        )
        root_page.add_child(instance=self.catalog_page)

        CatalogFilterCategory.objects.create(page=self.catalog_page, key="shower-doors", label="Shower Doors")
        CatalogFilterCategory.objects.create(page=self.catalog_page, key="railings", label="Railings")

        CatalogIndexItem.objects.create(
            page=self.catalog_page,
            title="Catalog 1",
            file_url="https://example.com/catalog-1.pdf",
            categories=["shower-doors"],
        )

    def test_catalogs_api_defaults_to_english_when_lang_missing(self):
        response = self.client.get("/api/catalogs")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "catalogs_cms.CatalogIndexPage")
        self.assertEqual(data["locale"], "en")

    def test_catalogs_api_defaults_to_english_when_lang_invalid(self):
        response = self.client.get("/api/catalogs?lang=pt")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["locale"], "en")

    def test_catalogs_api_returns_contract_shape(self):
        response = self.client.get("/api/catalogs?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("meta", data)
        self.assertIn("fields", data)
        self.assertIn("copy", data["fields"])
        self.assertIn("catalogs", data["fields"])

        copy_data = data["fields"]["copy"]
        self.assertIn("catalogs_eyebrow", copy_data)
        self.assertIn("catalogs_heading", copy_data)
        self.assertIn("catalogs_prev_aria", copy_data)
        self.assertIn("catalogs_next_aria", copy_data)
        self.assertIn("catalogs_dot_aria", copy_data)
        self.assertIn("filter_heading", copy_data)
        self.assertIn("filter_all_label", copy_data)
        self.assertIn("empty_state_text", copy_data)
        self.assertIn("categories", data["fields"])
        self.assertEqual(data["fields"]["categories"][0]["key"], "shower-doors")

        self.assertGreaterEqual(len(data["fields"]["catalogs"]), 1)
        first_item = data["fields"]["catalogs"][0]
        self.assertIn("title", first_item)
        self.assertIn("image", first_item)
        self.assertIn("file_url", first_item)
        self.assertIn("categories", first_item)
        self.assertEqual(first_item["categories"], ["shower-doors"])

    def test_catalogs_api_uses_uploaded_pdf_url_when_available(self):
        Document = get_document_model()
        pdf_file = SimpleUploadedFile("catalog.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        document = Document.objects.create(title="Catalog PDF", file=pdf_file)

        item = CatalogIndexItem.objects.create(
            page=self.catalog_page,
            title="Catalog with PDF",
            file_document=document,
            file_url="https://example.com/legacy.pdf",
        )

        response = self.client.get("/api/catalogs?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        target = next((entry for entry in data["fields"]["catalogs"] if entry["title"] == item.title), None)
        self.assertIsNotNone(target)
        self.assertIn("/documents/", target["file_url"])
        self.assertTrue(target["file_url"].endswith(".pdf"))

    def test_catalogs_api_requested_es_returns_en_locale_when_es_page_missing(self):
        response = self.client.get("/api/catalogs?lang=es")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["locale"], "en")

    def test_catalogs_preview_renders_astro_iframe_and_payload(self):
        request = RequestFactory().get("/admin/")
        response = self.catalog_page.serve_preview(request, mode_name="default")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("/catalogs/?lang=en", content)
        self.assertIn('"type": "catalogs_cms.CatalogIndexPage"', content)
