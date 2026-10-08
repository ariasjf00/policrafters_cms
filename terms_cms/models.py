from django.conf import settings
from django.db import models
from django.shortcuts import render

from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, Page, TranslatableMixin


class TermsPage(Page):
    intro_heading = models.CharField(max_length=255, blank=True)
    intro_body = models.TextField(blank=True)

    def serve_preview(self, request, mode_name):
        from terms_cms.api import serialize_terms_page

        lang = getattr(getattr(self, "locale", None), "language_code", "en")
        data = serialize_terms_page(self, request, lang)

        return render(
            request,
            "terms_cms/astro_preview.html",
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
            heading="Terms copy",
        ),
        InlinePanel("term_items", label="Terms"),
    ]


class TermItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "terms_cms.TermsPage",
        related_name="term_items",
        on_delete=models.CASCADE,
    )
    key = models.SlugField(max_length=120)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["translation_key", "locale"],
                name="unique_translation_key_locale_terms_cms_termitem",
            ),
            models.UniqueConstraint(
                fields=["page", "key"],
                name="terms_cms_termitem_unique_key_per_page",
            )
        ]

    def clean(self):
        super().clean()
        if self.locale_id is None and self.page_id:
            self.locale_id = self.page.locale_id

    panels = [
        FieldPanel("key"),
        FieldPanel("title"),
        FieldPanel("body"),
    ]
