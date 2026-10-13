from django.test import RequestFactory

from wagtail.models import Locale, Page, Site
from wagtail.test.utils import WagtailPageTestCase

from why_policrafters.models import (
    CertificationIssuer,
    IdentityItem,
    IssuerLicense,
    PartnerItem,
    WhyItem,
    WhyPolicraftersPage,
)


class WhyPolicraftersApiTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )

        self.page = WhyPolicraftersPage(
            title="Why Policrafters",
            intro_eyebrow="About us",
            intro_heading="Why Policrafters",
            intro_body=["We deliver quality projects.", "Certified and experienced team."],
            why_eyebrow="Why choose us",
            why_heading="Reasons to trust us",
            certifications_eyebrow="Certifications",
            certifications_heading="Licenses",
            certifications_body=["State-certified professionals."],
            identity_eyebrow="Identity",
            identity_heading="Our identity",
            partners_eyebrow="Partners",
            partners_heading="Manufacturers",
            partners_intro="We work with top manufacturers.",
            search_description="Why Policrafters page",
        )
        root_page.add_child(instance=self.page)

        WhyItem.objects.create(
            page=self.page,
            key="experience",
            heading="Experience",
            body=["More than 20 years in the industry."],
        )

        issuer = CertificationIssuer.objects.create(
            page=self.page,
            key="dbpr",
        )
        IssuerLicense.objects.create(
            page=issuer,
            label="Contractor",
            number="CPC1457998",
            caption="Active license",
        )

        IdentityItem.objects.create(
            page=self.page,
            key="mission",
            heading="Mission",
            body=["Deliver tailored and durable solutions."],
        )

        PartnerItem.objects.create(
            page=self.page,
            key="partner-a",
            body=["Strategic partnership for premium materials."],
        )

        self.es_locale, _ = Locale.objects.get_or_create(language_code="es")
        self.es_page = WhyPolicraftersPage(
            title="Por qué Policrafters",
            intro_heading="Por qué Policrafters",
            intro_body=["Creamos proyectos con estándares de calidad."],
        )
        root_page.add_child(instance=self.es_page)
        self.es_page.locale = self.es_locale
        self.es_page.save()

    def test_why_policrafters_api_returns_contract_shape(self):
        response = self.client.get("/api/why-policrafters-page?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "why_policrafters.WhyPolicraftersPage")
        self.assertEqual(data["locale"], "en")
        self.assertIn("meta", data)
        self.assertIn("fields", data)
        self.assertIn("why_items", data["fields"])
        self.assertIn("issuers", data["fields"])
        self.assertIn("identity_items", data["fields"])
        self.assertIn("partners", data["fields"])
        self.assertEqual(data["fields"]["why_items"][0]["key"], "experience")
        self.assertEqual(data["fields"]["issuers"][0]["licenses"][0]["number"], "CPC1457998")

    def test_why_policrafters_api_returns_spanish_locale_when_requested(self):
        response = self.client.get("/api/why-policrafters-page?lang=es")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["locale"], "es")
        self.assertEqual(response.json()["fields"]["intro_heading"], "Por qué Policrafters")

    def test_why_policrafters_api_falls_back_to_global_locale_match_when_site_root_excludes_page(self):
        root_page = Page.get_first_root_node()
        es_locale = Locale.objects.get(language_code="es")
        isolated_root = WhyPolicraftersPage(title="Isolated root")
        root_page.add_child(instance=isolated_root)
        isolated_root.locale = es_locale
        isolated_root.save()

        Site.objects.filter(is_default_site=True).update(root_page=isolated_root)

        response = self.client.get("/api/why-policrafters-page?lang=en")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["locale"], "en")
        self.assertEqual(data["fields"]["intro_heading"], "Why Policrafters")


class WhyPolicraftersPageRenderTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )
        self.page = WhyPolicraftersPage(
            title="Why Policrafters",
            intro_heading="Why Policrafters",
            intro_body=["Intro paragraph"],
        )
        root_page.add_child(instance=self.page)

    def test_why_policrafters_page_is_renderable(self):
        self.assertPageIsRenderable(self.page)

    def test_why_policrafters_preview_renders_astro_iframe_and_payload(self):
        request = RequestFactory().get("/admin/")
        response = self.page.serve_preview(request, mode_name="default")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("/why-policrafters?lang=en", content)
        self.assertIn('"type": "why_policrafters.WhyPolicraftersPage"', content)
