from django.test import TestCase
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Page, Site


class RedirectsApiTests(TestCase):
    def setUp(self):
        self.root_page = Page.get_first_root_node()
        self.site = Site.objects.create(
            hostname="redirects.test",
            root_page=self.root_page,
            is_default_site=True,
        )
        self.other_site = Site.objects.create(
            hostname="other-redirects.test",
            root_page=self.root_page,
        )

    def test_returns_contract_shape_without_locale_parameter(self):
        Redirect.objects.create(
            old_path="/old-collection/",
            site=self.site,
            redirect_link="https://policrafters.com/collections/new",
            is_permanent=True,
        )
        Redirect.objects.create(
            old_path="/temporary",
            site=None,
            redirect_link="/new-location",
            is_permanent=False,
        )
        Redirect.objects.create(
            old_path="/other-site-only",
            site=self.other_site,
            redirect_link="https://policrafters.com/other",
        )

        response = self.client.get("/api/redirects?locale=es")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["type"], "redirects.RedirectList")
        self.assertEqual(data["title"], "Redirects")
        self.assertEqual(data["locale"], "en")
        self.assertEqual(data["meta"], {})
        self.assertEqual(
            data["fields"]["items"],
            [
                {
                    "old_path": "/old-collection",
                    "new_path": "https://policrafters.com/collections/new",
                    "is_permanent": True,
                },
                {
                    "old_path": "/temporary",
                    "new_path": "/new-location",
                    "is_permanent": False,
                },
            ],
        )

    def test_page_redirects_are_exposed_as_relative_paths(self):
        target_page = Page(title="Target page", slug="target-page")
        self.root_page.add_child(instance=target_page)
        Redirect.objects.create(
            old_path="/old-page",
            site=self.site,
            redirect_page=target_page,
        )

        response = self.client.get("/api/redirects")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["fields"]["items"],
            [
                {
                    "old_path": "/old-page",
                    "new_path": "/target-page",
                    "is_permanent": True,
                }
            ],
        )

    def test_redirects_without_targets_are_omitted(self):
        Redirect.objects.create(
            old_path="/missing-target",
            site=self.site,
        )

        response = self.client.get("/api/redirects")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["fields"]["items"], [])
