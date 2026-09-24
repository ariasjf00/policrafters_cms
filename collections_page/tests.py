from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

from collections_page.models import (
    CollectionCategoryItem,
    CollectionIndexPage,
    CollectionProductItem,
    CollectionTypeItem,
)

from wagtail.images import get_image_model
from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase


class CollectionsApiTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )

        self.collections_page = CollectionIndexPage(
            title="Collections",
            hero_title="Collections",
            intro_text="Explore our lines.",
            empty_state_text="No products available.",
            search_description="Policrafters collections",
        )
        root_page.add_child(instance=self.collections_page)

        CollectionCategoryItem.objects.create(
            page=self.collections_page,
            key="shower-doors",
            label="Shower doors",
        )
        CollectionTypeItem.objects.create(
            page=self.collections_page,
            category_key="shower-doors",
            key="sliding",
            label="Sliding",
        )
        CollectionProductItem.objects.create(
            page=self.collections_page,
            category_key="shower-doors",
            type_key="sliding",
            title="Easy Slide",
            slug="easy-slide",
            image_alt="Easy Slide",
        )

    def test_collections_api_defaults_to_english_when_lang_missing(self):
        response = self.client.get("/api/collections")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "collections.CollectionIndexPage")
        self.assertEqual(data["locale"], "en")

    def test_collections_api_defaults_to_english_when_lang_invalid(self):
        response = self.client.get("/api/collections?lang=pt")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["locale"], "en")

    def test_collections_api_requested_es_returns_en_locale_when_es_page_missing(self):
        response = self.client.get("/api/collections?lang=es")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["locale"], "en")

    def test_collections_api_returns_contract_shape(self):
        response = self.client.get("/api/collections?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("meta", data)
        self.assertIn("fields", data)

        fields = data["fields"]
        self.assertIn("hero_title", fields)
        self.assertIn("intro_text", fields)
        self.assertIn("empty_state_text", fields)
        self.assertIn("categories", fields)

        self.assertEqual(fields["hero_title"], "Collections")
        self.assertEqual(fields["intro_text"], "Explore our lines.")
        self.assertEqual(fields["empty_state_text"], "No products available.")

        self.assertIn("search_description", data["meta"])
        self.assertNotIn("search_description_en", data["meta"])

        self.assertGreaterEqual(len(fields["categories"]), 1)
        first_category = fields["categories"][0]
        self.assertIn("key", first_category)
        self.assertIn("label", first_category)
        self.assertIn("has_products", first_category)
        self.assertIn("types", first_category)

        self.assertEqual(first_category["label"], "Shower doors")
        self.assertGreaterEqual(len(first_category["types"]), 1)
        first_type = first_category["types"][0]
        self.assertEqual(first_type["label"], "Sliding")
        self.assertGreaterEqual(len(first_type["products"]), 1)
        first_product = first_type["products"][0]
        self.assertEqual(first_product["title"], "Easy Slide")
        self.assertIn("image", first_product)
        self.assertIn("alt", first_product["image"])
        self.assertNotIn("alt_en", first_product["image"])

    def test_collections_api_preserves_category_type_and_product_order(self):
        CollectionCategoryItem.objects.create(
            page=self.collections_page,
            key="mirrors",
            label="Mirrors",
            sort_order=1,
        )

        CollectionTypeItem.objects.create(
            page=self.collections_page,
            category_key="shower-doors",
            key="hinged",
            label="Hinged",
            sort_order=1,
        )
        CollectionProductItem.objects.create(
            page=self.collections_page,
            category_key="shower-doors",
            type_key="hinged",
            title="Alpha Hinge",
            slug="alpha-hinge",
            sort_order=1,
        )

        response = self.client.get("/api/collections?lang=en")
        self.assertEqual(response.status_code, 200)

        categories = response.json()["fields"]["categories"]
        self.assertEqual(categories[0]["key"], "mirrors")
        self.assertEqual(categories[1]["key"], "shower-doors")

        shower_doors = categories[1]
        self.assertEqual(shower_doors["types"][0]["key"], "hinged")
        self.assertEqual(shower_doors["types"][1]["key"], "sliding")
        self.assertEqual(shower_doors["types"][0]["products"][0]["title"], "Alpha Hinge")

    def test_product_detail_api_resolves_full_slug(self):
        product = CollectionProductItem.objects.create(
            page=self.collections_page,
            category_key="shower-doors",
            type_key="fixed",
            title="Model 1",
            slug="model-1",
            image_alt="Model 1 image",
            product_eyebrow="Featured",
            product_heading="Model 1",
            intro_text_1="Intro paragraph one.",
            intro_text_2="Intro paragraph two.",
            technical_eyebrow="Technical Information",
            download_heading="Downloads",
            back_to_menu_label="Back to products menu",
        )

        response = self.client.get("/api/products?lang=en&slug=shower-doors/fixed/model-1")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "collections.ModelPage")
        self.assertEqual(data["slug"], "shower-doors/fixed/model-1")
        self.assertEqual(data["fields"]["collection"]["slug"], "shower-doors")
        self.assertEqual(data["fields"]["product_heading"], "Model 1")
        self.assertEqual(data["fields"]["back_to_menu_label"], "Back to products menu")

    def test_product_detail_api_serializes_gallery_pair_from_image_fields(self):
        buffer = BytesIO()
        PILImage = Image
        PILImage.new("RGB", (10, 10), color="white").save(buffer, format="PNG")
        valid_png = buffer.getvalue()

        WagtailImage = get_image_model()
        image_1 = WagtailImage.objects.create(
            title="Side view",
            file=SimpleUploadedFile("side.png", valid_png, content_type="image/png"),
        )
        image_2 = WagtailImage.objects.create(
            title="Bathroom view",
            file=SimpleUploadedFile("bath.png", valid_png, content_type="image/png"),
        )

        product = CollectionProductItem.objects.create(
            page=self.collections_page,
            category_key="shower-doors",
            type_key="fixed",
            title="Model 1",
            slug="shower-doors/fixed/model-1",
            gallery_image_1=image_1,
            gallery_image_2=image_2,
            gallery_image_1_alt="Side view of the shower",
            gallery_image_2_alt="Full bathroom with fixed shower door",
        )

        response = self.client.get("/api/products?lang=en&slug=shower-doors/fixed/model-1")
        self.assertEqual(response.status_code, 200)

        gallery_pair = response.json()["fields"]["gallery_pair"]
        self.assertEqual(len(gallery_pair), 2)
        self.assertEqual(gallery_pair[0]["alt"], "Side view of the shower")
        self.assertEqual(gallery_pair[1]["alt"], "Full bathroom with fixed shower door")


class CollectionsInlineLocaleTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )

        self.collections_page = CollectionIndexPage(
            title="Collections",
            hero_title="Collections",
        )
        root_page.add_child(instance=self.collections_page)

    def test_new_category_inherits_page_locale(self):
        item = CollectionCategoryItem(
            page=self.collections_page,
            key="pergolas",
            label="Pergolas",
        )

        item.full_clean()

        self.assertEqual(item.locale_id, self.collections_page.locale_id)

    def test_new_type_inherits_page_locale(self):
        item = CollectionTypeItem(
            page=self.collections_page,
            key="sliding",
            label="Sliding",
            category_key="pergolas",
        )

        item.full_clean()

        self.assertEqual(item.locale_id, self.collections_page.locale_id)

    def test_new_product_inherits_page_locale(self):
        item = CollectionProductItem(
            page=self.collections_page,
            title="Pergola Thermal",
            slug="pergola-thermal",
            category_key="pergolas",
            type_key="sliding",
        )

        item.full_clean()

        self.assertEqual(item.locale_id, self.collections_page.locale_id)
