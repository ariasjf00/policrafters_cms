from django.conf import settings
from django.db import models
from django.shortcuts import render

from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, Page, TranslatableMixin


class WarrantyPage(Page):
    intro_heading = models.CharField(max_length=255, blank=True)
    intro_body = models.TextField(blank=True)

    def serve_preview(self, request, mode_name):
        from warranty_cms.api import serialize_warranty_page

        lang = getattr(getattr(self, "locale", None), "language_code", "en")
        data = serialize_warranty_page(self, request, lang)

        return render(
            request,
            "warranty_cms/warranty_astro_preview.html",
            {
                "preview_data": data,
                "preview_lang": lang,
                "astro_preview_url": settings.ASTRO_PREVIEW_URL,
            },
        )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("intro_heading"),
                FieldPanel("intro_body"),
                FieldPanel("search_description"),
            ],
            heading="Warranty copy",
        ),
        InlinePanel("sections", label="Warranty sections"),
    ]


class WarrantySection(TranslatableMixin, ClusterableModel, Orderable):
    page = ParentalKey(
        "warranty_cms.WarrantyPage",
        related_name="sections",
        on_delete=models.CASCADE,
    )
    key = models.SlugField(max_length=120)
    title = models.CharField(max_length=255)
    intro = models.TextField(blank=True)
    column = models.CharField(
        max_length=10,
        choices=[("left", "Left"), ("right", "Right")],
        default="left",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["translation_key", "locale"],
                name="unique_translation_key_locale_warranty_cms_warrantysection",
            ),
            models.UniqueConstraint(
                fields=["page", "key"],
                name="warranty_cms_warrantysection_unique_key_per_page",
            ),
        ]

    def clean(self):
        super().clean()
        if self.locale_id is None and self.page_id:
            self.locale_id = self.page.locale_id

    panels = [
        FieldPanel("key"),
        FieldPanel("title"),
        FieldPanel("column"),
        FieldPanel("intro"),
        InlinePanel("items", label="Items"),
    ]


class WarrantyItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "warranty_cms.WarrantySection",
        related_name="items",
        on_delete=models.CASCADE,
    )
    label = models.CharField(max_length=255, blank=True)
    text = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["translation_key", "locale"],
                name="unique_translation_key_locale_warranty_cms_warrantyitem",
            ),
        ]

    def clean(self):
        super().clean()
        if self.locale_id is None and self.page_id:
            self.locale_id = self.page.locale_id

    panels = [
        FieldPanel("label"),
        FieldPanel("text"),
    ]
