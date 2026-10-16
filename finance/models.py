import uuid

from django.conf import settings
from django.db import models
from django.db.models import Max
from django.shortcuts import render
from django.utils.text import slugify

from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, Page, TranslatableMixin


class FinancePage(Page):
    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    hero_image_alt = models.CharField(max_length=255, blank=True)
    intro_heading = models.CharField(max_length=255, blank=True)
    intro_body = models.TextField(blank=True)

    contact_heading = models.CharField(max_length=255, blank=True)
    contact_phone_display = models.CharField(max_length=120, blank=True)
    contact_phone_href = models.CharField(max_length=120, blank=True)
    contact_email_label = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)

    def _reindex_steps_order(self):
        steps = list(FinanceStep.objects.filter(page_id=self.pk).order_by("pk"))
        for index, step in enumerate(steps):
            if step.sort_order != index:
                FinanceStep.objects.filter(pk=step.pk).update(sort_order=index)

        if hasattr(self, "_prefetched_objects_cache"):
            self._prefetched_objects_cache.pop("steps", None)
        self.refresh_from_db()

    def save(self, *args, **kwargs):
        saved = super().save(*args, **kwargs)
        self._reindex_steps_order()
        return saved

    def save_revision(self, *args, **kwargs):
        revision = super().save_revision(*args, **kwargs)
        self._reindex_steps_order()
        return revision

    def serve_preview(self, request, mode_name):
        from finance.api import serialize_finance_page

        lang = getattr(getattr(self, "locale", None), "language_code", "en")
        data = serialize_finance_page(self, request, lang)

        return render(
            request,
            "finance/astro_preview.html",
            {
                "preview_data": data,
                "preview_lang": lang,
                "astro_preview_url": settings.ASTRO_PREVIEW_URL,
            },
        )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("hero_image"),
                FieldPanel("hero_image_alt"),
                FieldPanel("intro_heading"),
                FieldPanel("intro_body"),
                FieldPanel("contact_heading"),
                FieldPanel("contact_phone_display"),
                FieldPanel("contact_phone_href"),
                FieldPanel("contact_email_label"),
                FieldPanel("contact_email"),
                FieldPanel("search_description"),
            ],
            heading="Finance copy",
        ),
        InlinePanel("steps", label="Finance steps"),
    ]


class FinanceStep(TranslatableMixin, Orderable):
    page = ParentalKey(
        "finance.FinancePage",
        related_name="steps",
        on_delete=models.CASCADE,
    )
    key = models.SlugField(max_length=120)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    column = models.CharField(
        max_length=10,
        choices=[("left", "Left"), ("right", "Right")],
        default="left",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["translation_key", "locale"],
                name="unique_translation_key_locale_finance_financestep",
            ),
            models.UniqueConstraint(
                fields=["page", "key"],
                name="finance_financestep_unique_key_per_page",
            ),
        ]

    def clean(self):
        super().clean()
        if self.page_id:
            self.locale_id = self.page.locale_id

    def _ensure_unique_translation_key_for_locale(self):
        if self.locale_id is None:
            return

        duplicate_exists = FinanceStep.objects.filter(
            translation_key=self.translation_key,
            locale_id=self.locale_id,
        ).exclude(pk=self.pk).exists()
        if duplicate_exists:
            self.translation_key = uuid.uuid4()

    def _ensure_unique_key_per_page(self):
        if not self.page_id:
            return

        base_key = (self.key or "").strip()
        if not base_key:
            base_key = slugify(self.title or "") or "step"

        base_key = base_key[:120]
        candidate = base_key
        suffix = 2

        while FinanceStep.objects.filter(page_id=self.page_id, key=candidate).exclude(pk=self.pk).exists():
            suffix_text = f"-{suffix}"
            candidate = f"{base_key[: 120 - len(suffix_text)]}{suffix_text}"
            suffix += 1

        self.key = candidate

    @classmethod
    def normalize_page_sort_order(cls, page_id):
        items = list(cls.objects.filter(page_id=page_id).order_by("sort_order", "pk"))
        for index, item in enumerate(items):
            if item.sort_order != index:
                cls.objects.filter(pk=item.pk).update(sort_order=index)

    def save(self, *args, **kwargs):
        if self.page_id:
            self.locale_id = self.page.locale_id
            if self.sort_order is None:
                max_sort_order = (
                    FinanceStep.objects.filter(page_id=self.page_id)
                    .aggregate(max_sort_order=Max("sort_order"))
                    .get("max_sort_order")
                    or -1
                )
                self.sort_order = max_sort_order + 1
        self._ensure_unique_translation_key_for_locale()
        self._ensure_unique_key_per_page()
        saved = super().save(*args, **kwargs)
        if self.page_id:
            FinanceStep.normalize_page_sort_order(self.page_id)
        return saved

    panels = [
        FieldPanel("key"),
        FieldPanel("title"),
        FieldPanel("subtitle"),
        FieldPanel("column"),
        FieldPanel("body"),
    ]
