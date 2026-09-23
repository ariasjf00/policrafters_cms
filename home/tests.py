from home.models import HomeContactLinkItem, HomePage
from shared_cms.models import DirectContactBlock, DirectContactLinkItem

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.utils import translation
from wagtail.admin.views.pages.edit import EditView
from wagtail.admin.wagtail_hooks import PageListingViewLiveButton
from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase
from policrafters_cms.middleware import force_preview_locale
from home.templatetags.localized_urls import add_locale_query


class HomeSetUpTests(WagtailPageTestCase):
    """
    Tests for basic page structure setup and HomePage creation.
    """

    def test_root_create(self):
        root_page = Page.objects.get(pk=1)
        self.assertIsNotNone(root_page)

    def test_homepage_create(self):
        root_page = Page.objects.get(pk=1)
        homepage = HomePage(title="Home")
        root_page.add_child(instance=homepage)
        self.assertTrue(HomePage.objects.filter(title="Home").exists())


class HomeTests(WagtailPageTestCase):
    """
    Tests for homepage functionality and rendering.
    """

    def setUp(self):
        """
        Create a homepage instance for testing.
        """
        root_page = Page.get_first_root_node()
        Site.objects.create(hostname="testsite", root_page=root_page, is_default_site=True)
        self.homepage = HomePage(title="Home")
        root_page.add_child(instance=self.homepage)

    def test_homepage_is_renderable(self):
        self.assertPageIsRenderable(self.homepage)

    def test_homepage_template_used(self):
        response = self.client.get(self.homepage.url)
        self.assertTemplateUsed(response, "home/home_page.html")


class LocaleOverrideMiddlewareTests(TestCase):
    def test_force_preview_locale_from_querystring(self):
        request = RequestFactory().get("/home/?lang=es")
        request.LANGUAGE_CODE = "en"

        translation.deactivate()
        force_preview_locale(request)

        self.assertEqual(request.LANGUAGE_CODE, "es")
        self.assertEqual(translation.get_language(), "es")

    def test_force_preview_locale_from_public_querystring(self):
        request = RequestFactory().get("/?lang=en")
        request.LANGUAGE_CODE = "es"

        translation.activate("es")
        force_preview_locale(request)

        self.assertEqual(request.LANGUAGE_CODE, "en")
        self.assertEqual(translation.get_language(), "en")

    def test_force_preview_locale_from_page_id_in_admin_preview_route(self):
        root_page = Page.get_first_root_node()
        homepage = HomePage(title="Home")
        root_page.add_child(instance=homepage)

        request = RequestFactory().get(f"/admin/pages/{homepage.id}/edit/preview/")
        request.LANGUAGE_CODE = "es"

        translation.deactivate()
        force_preview_locale(request)

        self.assertEqual(request.LANGUAGE_CODE, "en")
        self.assertEqual(translation.get_language(), "en")

    def test_page_listing_view_live_button_uses_page_locale(self):
        root_page = Page.get_first_root_node()
        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            Site.objects.create(hostname="testsite", root_page=root_page, is_default_site=True)

        homepage = HomePage(title="Home")
        root_page.add_child(instance=homepage)

        button = PageListingViewLiveButton(
            page=homepage,
            url="http://localhost:8000/",
            priority=6,
        )

        self.assertIsNotNone(button.url)
        self.assertIn("lang=en", button.url)

    def test_add_locale_query_appends_lang_parameter(self):
        url = add_locale_query("http://localhost:8000/", "es")

        self.assertIn("lang=es", url)

    def test_edit_view_preview_url_uses_page_locale(self):
        root_page = Page.get_first_root_node()
        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            Site.objects.create(hostname="testsite", root_page=root_page, is_default_site=True)

        homepage = HomePage(title="Home")
        root_page.add_child(instance=homepage)

        view = EditView()
        view.page = homepage

        preview_url = view.get_preview_url()

        self.assertIn("lang=en", preview_url)


class HomeApiTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )

        self.homepage = HomePage(
            title="Home",
            hero_eyebrow="HOME EYEBROW",
            hero_heading="HOME HEADING",
            hero_cta="CONTACT",
        )
        root_page.add_child(instance=self.homepage)

    def test_home_api_defaults_to_english_when_lang_missing(self):
        response = self.client.get("/api/home")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["locale"], "en")
        self.assertIsInstance(data["fields"]["copy"]["hero_heading"], str)
        self.assertEqual(data["fields"]["copy"]["hero_heading"], "HOME HEADING")

    def test_home_api_defaults_to_english_when_lang_invalid(self):
        response = self.client.get("/api/home?lang=pt")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["locale"], "en")
        self.assertIsInstance(data["fields"]["copy"]["hero_cta"], str)
        self.assertEqual(data["fields"]["copy"]["hero_cta"], "CONTACT")

    def test_home_api_requested_es_returns_en_locale_when_es_page_missing(self):
        response = self.client.get("/api/home?lang=es")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["locale"], "en")

    def test_home_api_does_not_include_catalogs_array(self):
        response = self.client.get("/api/home?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertNotIn("catalogs", data["fields"])

    def test_home_api_does_not_include_catalogs_copy_keys(self):
        response = self.client.get("/api/home?lang=en")
        self.assertEqual(response.status_code, 200)

        copy_data = response.json()["fields"]["copy"]
        self.assertNotIn("catalogs_eyebrow", copy_data)
        self.assertNotIn("catalogs_heading", copy_data)
        self.assertNotIn("catalogs_prev_aria", copy_data)
        self.assertNotIn("catalogs_next_aria", copy_data)
        self.assertNotIn("catalogs_dot_aria", copy_data)

    def test_home_api_does_not_include_contact_links(self):
        response = self.client.get("/api/home?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertNotIn("contact_links", data["fields"])

    def test_home_api_returns_uploaded_video_urls_from_media(self):
        self.homepage.hero_video_horizontal = SimpleUploadedFile(
            "hero-horizontal.mp4",
            b"video-data-horizontal",
            content_type="video/mp4",
        )
        self.homepage.hero_video_vertical = SimpleUploadedFile(
            "hero-vertical.mp4",
            b"video-data-vertical",
            content_type="video/mp4",
        )
        self.homepage.save()

        response = self.client.get("/api/home?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("/media/videos/home/hero-horizontal", data["fields"]["hero_video_horizontal"])
        self.assertIn("/media/videos/home/hero-vertical", data["fields"]["hero_video_vertical"])


class DirectContactApiTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )

        self.homepage = HomePage(
            title="Home",
            hero_heading="Home heading",
            contact_heading="Get in touch",
            contact_cta="Contact us",
        )
        root_page.add_child(instance=self.homepage)

        HomeContactLinkItem.objects.create(
            page=self.homepage,
            locale=self.homepage.locale,
            title="Whatsapp",
            description="Chat with our team",
            url="https://wa.me/123456789",
        )

    def test_direct_contact_api_returns_contract_shape(self):
        response = self.client.get("/api/direct-contact?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "shared_cms.DirectContactBlock")
        self.assertIn("fields", data)
        self.assertIn("copy", data["fields"])
        self.assertIn("contact_links", data["fields"])

        self.assertEqual(data["fields"]["copy"]["contact_heading"], "Get in touch")
        self.assertEqual(data["fields"]["copy"]["contact_cta"], "Contact us")
        self.assertGreaterEqual(len(data["fields"]["contact_links"]), 1)

    def test_direct_contact_api_defaults_to_english_when_lang_invalid(self):
        response = self.client.get("/api/direct-contact?lang=pt")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["locale"], "en")

    def test_direct_contact_api_prefers_snippet_when_available(self):
        block = DirectContactBlock.objects.create(
            locale=self.homepage.locale,
            title="Global direct contact",
            contact_heading="Snippet heading",
            contact_cta="Snippet CTA",
        )
        DirectContactLinkItem.objects.create(
            block=block,
            locale=self.homepage.locale,
            sort_order=2,
            title="Email",
            description="Write us",
            url="mailto:info@policrafters.com",
        )
        DirectContactLinkItem.objects.create(
            block=block,
            locale=self.homepage.locale,
            sort_order=1,
            title="Phone",
            description="Call us",
            url="tel:+18001112222",
        )

        response = self.client.get("/api/direct-contact?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["title"], "Global direct contact")
        self.assertEqual(data["fields"]["copy"]["contact_heading"], "Snippet heading")
        self.assertEqual(data["fields"]["copy"]["contact_cta"], "Snippet CTA")
        self.assertEqual(data["fields"]["contact_links"][0]["title"], "Phone")
        self.assertEqual(data["fields"]["contact_links"][1]["title"], "Email")
