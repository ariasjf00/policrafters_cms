from contact_cms.models import ContactLocationItem, ContactPage

from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase


class ContactApiTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )

        self.contact_page = ContactPage(
            title="Contact Us",
            heading="Get in touch",
            intro="Talk with our team.",
            phone_label="Phone",
            email_label="Email",
            locations_heading="Our locations",
            locations_aria="Locations list",
            learn_more="Learn more",
            phone_display="+1 800 111 2222",
            phone_href="tel:+18001112222",
            email="info@policrafters.com",
        )
        root_page.add_child(instance=self.contact_page)

        ContactLocationItem.objects.create(
            page=self.contact_page,
            name="Miami",
            address_label="Address",
            street="123 Main St",
            city="Miami, FL",
            url="https://example.com/miami",
        )

    def test_contact_api_defaults_to_english_when_lang_missing(self):
        response = self.client.get("/api/contact-page")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "contact_cms.ContactPage")
        self.assertEqual(data["locale"], "en")

    def test_contact_api_defaults_to_english_when_lang_invalid(self):
        response = self.client.get("/api/contact-page?lang=pt")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["locale"], "en")

    def test_contact_api_requested_es_returns_en_locale_when_es_page_missing(self):
        response = self.client.get("/api/contact-page?lang=es")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["locale"], "en")

    def test_contact_api_returns_contract_shape(self):
        response = self.client.get("/api/contact-page?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("fields", data)
        self.assertIn("copy", data["fields"])
        self.assertIn("contact", data["fields"])
        self.assertIn("locations", data["fields"])

        self.assertEqual(data["fields"]["copy"]["heading"], "Get in touch")
        self.assertEqual(data["fields"]["contact"]["phone_href"], "tel:+18001112222")
        self.assertGreaterEqual(len(data["fields"]["locations"]), 1)


class ContactPageRenderTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )

        self.contact_page = ContactPage(title="Contact Us", heading="Get in touch")
        root_page.add_child(instance=self.contact_page)

    def test_contact_page_is_renderable(self):
        self.assertPageIsRenderable(self.contact_page)
