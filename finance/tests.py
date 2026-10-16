from django.test import RequestFactory

from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase

from finance.models import FinancePage, FinanceStep


class FinanceApiTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )

        self.page = FinancePage(
            title="Finance",
            intro_heading="Finance options",
            intro_body="Choose a financing plan that matches your project.",
            contact_heading="Contact for finance details",
            contact_phone_display="+1 800 222 3333",
            contact_phone_href="tel:+18002223333",
            contact_email_label="Email",
            contact_email="finance@policrafters.com",
            search_description="Finance page",
        )
        root_page.add_child(instance=self.page)

        FinanceStep.objects.create(
            page=self.page,
            key="application",
            title="Submit your application",
            subtitle="Step one",
            body="Complete your basic application details.",
            column="left",
        )
        FinanceStep.objects.create(
            page=self.page,
            key="review",
            title="Review and approval",
            subtitle="Step two",
            body="Our team reviews your eligibility and confirms terms.",
            column="right",
        )

    def test_finance_api_defaults_to_english_when_lang_missing(self):
        response = self.client.get("/api/finance-page")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["locale"], "en")

    def test_finance_api_defaults_to_english_when_lang_invalid(self):
        response = self.client.get("/api/finance-page?lang=pt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["locale"], "en")

    def test_finance_api_returns_contract_shape(self):
        response = self.client.get("/api/finance-page?lang=en")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "finance.FinancePage")
        self.assertIn("meta", data)
        self.assertIn("fields", data)
        self.assertIn("hero_image", data["fields"])
        self.assertIn("steps", data["fields"])
        self.assertIn("contact", data["fields"])
        self.assertEqual(data["fields"]["intro_heading"], "Finance options")
        self.assertEqual(len(data["fields"]["steps"]), 2)
        self.assertEqual(data["fields"]["steps"][0]["key"], "application")
        self.assertEqual(data["fields"]["contact"]["email"], "finance@policrafters.com")


class FinancePageRenderTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )
        self.page = FinancePage(
            title="Finance",
            intro_heading="Finance options",
            intro_body="Choose a financing plan that matches your project.",
        )
        root_page.add_child(instance=self.page)

    def test_finance_page_is_renderable(self):
        self.assertPageIsRenderable(self.page)

    def test_finance_page_preview_renders_astro_iframe_and_payload(self):
        request = RequestFactory().get("/admin/")
        response = self.page.serve_preview(request, mode_name="default")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("/finance?lang=en", content)
        self.assertIn('"type": "finance.FinancePage"', content)


class FinanceStepUniquenessTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.update_or_create(
            hostname="testsite",
            defaults={"root_page": root_page, "is_default_site": True},
        )
        self.page = FinancePage(
            title="Finance",
            intro_heading="Finance options",
            intro_body="Choose a financing plan.",
        )
        root_page.add_child(instance=self.page)

    def test_duplicate_translation_key_is_regenerated_on_save(self):
        original = FinanceStep.objects.create(
            page=self.page,
            key="application",
            title="Submit your application",
            body="Original body.",
            column="left",
        )

        duplicated = FinanceStep(
            page=self.page,
            key="review",
            title="Review and approval",
            body="Duplicated row body.",
            column="right",
            translation_key=original.translation_key,
            locale_id=self.page.locale_id,
        )
        duplicated.save()

        self.assertNotEqual(duplicated.translation_key, original.translation_key)

    def test_duplicate_key_is_auto_suffixed_on_save(self):
        FinanceStep.objects.create(
            page=self.page,
            key="application",
            title="Submit your application",
            body="Original body.",
            column="left",
        )

        duplicated_key_step = FinanceStep(
            page=self.page,
            key="application",
            title="Review and approval",
            body="Duplicated key body.",
            column="right",
        )
        duplicated_key_step.save()

        self.assertEqual(duplicated_key_step.key, "application-2")

    def test_page_sort_order_is_reindexed_without_changing_current_order(self):
        step_1 = FinanceStep.objects.create(
            page=self.page,
            key="step-1",
            title="Step one",
            body="First body.",
            column="left",
        )
        step_2 = FinanceStep.objects.create(
            page=self.page,
            key="step-2",
            title="Step two",
            body="Second body.",
            column="right",
        )
        step_3 = FinanceStep.objects.create(
            page=self.page,
            key="step-3",
            title="Step three",
            body="Third body.",
            column="left",
        )

        current_order = [step_3.pk, step_1.pk, step_2.pk]
        for index, pk in enumerate(current_order):
            FinanceStep.objects.filter(pk=pk).update(sort_order=index)

        FinanceStep.normalize_page_sort_order(self.page.pk)

        ordered_keys = list(
            FinanceStep.objects.filter(page=self.page)
            .order_by("sort_order", "pk")
            .values_list("key", flat=True)
        )

        self.assertEqual(ordered_keys, ["step-3", "step-1", "step-2"])

    def test_page_save_reindexes_steps_by_pk(self):
        step_1 = FinanceStep.objects.create(
            page=self.page,
            key="one",
            title="One",
            body="First body.",
            column="left",
        )
        step_2 = FinanceStep.objects.create(
            page=self.page,
            key="two",
            title="Two",
            body="Second body.",
            column="right",
        )
        step_3 = FinanceStep.objects.create(
            page=self.page,
            key="three",
            title="Three",
            body="Third body.",
            column="left",
        )

        FinanceStep.objects.filter(pk=step_1.pk).update(sort_order=2)
        FinanceStep.objects.filter(pk=step_2.pk).update(sort_order=0)
        FinanceStep.objects.filter(pk=step_3.pk).update(sort_order=1)

        self.page.save()

        ordered_keys = list(
            FinanceStep.objects.filter(page=self.page)
            .order_by("sort_order", "pk")
            .values_list("key", flat=True)
        )

        self.assertEqual(ordered_keys, ["one", "two", "three"])

    def test_api_serialization_does_not_mutate_sort_order(self):
        step_1 = FinanceStep.objects.create(
            page=self.page,
            key="one",
            title="One",
            body="First body.",
            column="left",
        )
        step_2 = FinanceStep.objects.create(
            page=self.page,
            key="two",
            title="Two",
            body="Second body.",
            column="right",
        )
        step_3 = FinanceStep.objects.create(
            page=self.page,
            key="three",
            title="Three",
            body="Third body.",
            column="left",
        )

        FinanceStep.objects.filter(pk=step_1.pk).update(sort_order=0)
        FinanceStep.objects.filter(pk=step_2.pk).update(sort_order=1)
        FinanceStep.objects.filter(pk=step_3.pk).update(sort_order=2)

        response = self.client.get("/api/finance-page?lang=en")
        self.assertEqual(response.status_code, 200)

        ordered_keys = list(
            FinanceStep.objects.filter(page=self.page)
            .order_by("sort_order", "pk")
            .values_list("key", flat=True)
        )

        self.assertEqual(ordered_keys, ["one", "two", "three"])
        self.assertEqual(
            [step["key"] for step in response.json()["fields"]["steps"]],
            ["one", "two", "three"],
        )
