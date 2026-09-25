from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

from wagtail.images import get_image_model
from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase

from services.models import ServiceItem, ServicesPage


class ServicesApiTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )

        self.page = ServicesPage(
            title="Services",
            intro_eyebrow="What we do",
            intro_heading="Our Services",
            intro_text="We provide integral support.",
            search_description="Services page",
        )
        root_page.add_child(instance=self.page)

        ServiceItem.objects.create(
            page=self.page,
            key="design",
            heading="Design",
            subtitle="Interior and architecture",
            body=[
                "Discovery and concept definition.",
                "Material and finish recommendations.",
                "Technical coordination and delivery.",
            ],
            image_alt="Design service",
        )

    def test_services_api_contract_shape(self):
        response = self.client.get("/api/services?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "services.ServicesPage")
        self.assertEqual(data["locale"], "en")
        self.assertEqual(data["fields"]["intro_heading"], "Our Services")
        self.assertIn("services", data["fields"])

        services = data["fields"]["services"]
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]["key"], "design")
        self.assertEqual(services[0]["heading"], "Design")
        self.assertEqual(len(services[0]["body"]), 3)

    def test_services_api_serializes_image_payload(self):
        buffer = BytesIO()
        Image.new("RGB", (10, 10), color="white").save(buffer, format="PNG")
        valid_png = buffer.getvalue()

        image = get_image_model().objects.create(
            title="Services hero",
            file=SimpleUploadedFile("hero.png", valid_png, content_type="image/png"),
        )

        self.page.hero_image = image
        self.page.hero_image_alt = "Services Hero"
        self.page.save(update_fields=["hero_image", "hero_image_alt"])

        service_item = ServiceItem.objects.first()
        service_item.image = image
        service_item.save(update_fields=["image"])

        response = self.client.get("/api/services?lang=en")
        self.assertEqual(response.status_code, 200)

        payload = response.json()["fields"]
        self.assertIn("url", payload["hero_image"])
        self.assertEqual(payload["hero_image"]["alt"], "Services Hero")
        self.assertIn("url", payload["services"][0]["image"])
        self.assertEqual(payload["services"][0]["image"]["alt"], "Design service")

    def test_services_preview_renders_astro_iframe_and_payload(self):
        request = RequestFactory().get("/admin/")
        response = self.page.serve_preview(request, mode_name="default")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn('/services/?lang=en', content)
        self.assertIn('"type": "services.ServicesPage"', content)
