from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

from wagtail.images import get_image_model
from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase

from renovations.models import (
    RenovationCategoryItem,
    RenovationIndexPage,
    RenovationProductItem,
    RenovationTypeItem,
)


class RenovationApiTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )

        self.page = RenovationIndexPage(
            title="Renovations",
            hero_title="Renovations",
            intro_text="Transform your spaces.",
            empty_state_text="No renovation projects available yet.",
            search_description="Renovation projects",
        )
        root_page.add_child(instance=self.page)

        RenovationCategoryItem.objects.create(
            page=self.page,
            key="commercial",
            label="Commercial",
            show_type_filters=True,
        )
        RenovationTypeItem.objects.create(
            page=self.page,
            category_key="commercial",
            key="facades",
            label="Facades",
        )
        RenovationProductItem.objects.create(
            page=self.page,
            category_key="commercial",
            type_key="facades",
            title="Project Alpha",
            slug="project-alpha",
            image_alt="Project Alpha",
        )

        RenovationCategoryItem.objects.create(
            page=self.page,
            key="partners",
            label="Partners",
            show_type_filters=False,
            sort_order=1,
        )
        RenovationProductItem.objects.create(
            page=self.page,
            category_key="partners",
            title="Partner Studio",
            slug="partner-studio",
            image_alt="Partner Studio",
            sort_order=1,
        )

    def test_renovations_api_contract_shape(self):
        response = self.client.get("/api/renovations?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "renovations.RenovationIndexPage")
        self.assertEqual(data["locale"], "en")
        self.assertEqual(data["fields"]["hero_title"], "Renovations")
        self.assertIn("categories", data["fields"])

        categories = data["fields"]["categories"]
        self.assertGreaterEqual(len(categories), 2)

        commercial = next(cat for cat in categories if cat["key"] == "commercial")
        self.assertEqual(commercial["label"], "Commercial")
        self.assertTrue(commercial["has_products"])
        self.assertEqual(commercial["types"][0]["key"], "facades")
        self.assertEqual(commercial["types"][0]["products"][0]["title"], "Project Alpha")

        partners = next(cat for cat in categories if cat["key"] == "partners")
        self.assertEqual(partners["label"], "Partners")
        self.assertFalse(partners["show_type_filters"])
        self.assertTrue(partners["has_products"])
        self.assertEqual(partners["types"][0]["products"][0]["title"], "Partner Studio")

    def test_renovations_api_serializes_image_payload(self):
        buffer = BytesIO()
        Image.new("RGB", (10, 10), color="white").save(buffer, format="PNG")
        valid_png = buffer.getvalue()

        image = get_image_model().objects.create(
            title="Renovation preview",
            file=SimpleUploadedFile("preview.png", valid_png, content_type="image/png"),
        )
        product = RenovationProductItem.objects.filter(category_key="commercial").first()
        product.image = image
        product.save(update_fields=["image"])

        response = self.client.get("/api/renovations?lang=en")
        self.assertEqual(response.status_code, 200)
        preview = next(
            product_payload
            for category in response.json()["fields"]["categories"]
            for type_item in category["types"]
            for product_payload in type_item["products"]
            if product_payload["title"] == "Project Alpha"
        )
        self.assertIn("image", preview)
        self.assertIn("url", preview["image"])
        self.assertEqual(preview["image"]["alt"], "Project Alpha")
