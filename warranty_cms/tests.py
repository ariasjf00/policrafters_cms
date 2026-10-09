from django.test import RequestFactory

from wagtail.models import Locale, Page, Site
from wagtail.test.utils import WagtailPageTestCase

from warranty_cms.models import WarrantyItem, WarrantyPage, WarrantySection


class WarrantyApiTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )

        self.page = WarrantyPage(
            title="Warranty",
            intro_heading="Warranty",
            intro_body="Protect your project with our warranty coverage.",
            search_description="Warranty page",
        )
        root_page.add_child(instance=self.page)

        self.section = WarrantySection.objects.create(
            page=self.page,
            key="coverage",
            title="Coverage",
            intro="What is covered.",
            column="left",
        )
        WarrantyItem.objects.create(
            page=self.section,
            label="Product",
            text="All coated products are covered for the first year.",
        )

        self.es_locale, _ = Locale.objects.get_or_create(language_code="es")
        self.es_page = WarrantyPage(title="Garantía", intro_heading="Garantía", intro_body="Cubre tu proyecto.")
        root_page.add_child(instance=self.es_page)
        self.es_page.locale = self.es_locale
        self.es_page.save()

        self.es_section = WarrantySection.objects.create(
            page=self.es_page,
            key="coverage",
            title="Cobertura",
            intro="Qué está cubierto.",
            column="left",
        )
        WarrantyItem.objects.create(
            page=self.es_section,
            label="Producto",
            text="Todos los productos recubiertos tienen garantía durante el primer año.",
        )

    def test_warranty_api_returns_contract_shape(self):
        response = self.client.get("/api/warranty-page?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "warranty.WarrantyPage")
        self.assertIn("meta", data)
        self.assertIn("fields", data)
        self.assertIn("sections", data["fields"])
        self.assertEqual(data["fields"]["intro_heading"], "Warranty")
        self.assertEqual(len(data["fields"]["sections"]), 1)
        self.assertEqual(data["fields"]["sections"][0]["key"], "coverage")

    def test_warranty_api_returns_spanish_locale_when_requested(self):
        response = self.client.get("/api/warranty-page?lang=es")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["locale"], "es")
        self.assertEqual(response.json()["fields"]["intro_heading"], "Garantía")


class WarrantyPageRenderTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )
        self.page = WarrantyPage(
            title="Warranty",
            intro_heading="Warranty",
            intro_body="Protect your project with our warranty coverage.",
        )
        root_page.add_child(instance=self.page)

        self.section = WarrantySection.objects.create(
            page=self.page,
            key="coverage",
            title="Coverage",
            intro="What is covered.",
            column="left",
        )
        WarrantyItem.objects.create(
            page=self.section,
            label="Product",
            text="All coated products are covered for the first year.",
        )

    def test_warranty_page_is_renderable(self):
        self.assertPageIsRenderable(self.page)

    def test_warranty_page_preview_renders_astro_iframe_and_payload(self):
        request = RequestFactory().get("/admin/")
        response = self.page.serve_preview(request, mode_name="default")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("/warranty/?lang=en", content)
        self.assertIn('"type": "warranty.WarrantyPage"', content)
