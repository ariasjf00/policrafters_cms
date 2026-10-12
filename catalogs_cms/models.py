from django.conf import settings
from django.db import models
from django.shortcuts import render

from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, Page, TranslatableMixin


class CatalogIndexPage(Page):
    catalogs_eyebrow = models.CharField(max_length=255, blank=True)
    catalogs_heading = models.CharField(max_length=255, blank=True)
    catalogs_prev_aria = models.CharField(max_length=255, blank=True)
    catalogs_next_aria = models.CharField(max_length=255, blank=True)
    catalogs_dot_aria = models.CharField(max_length=255, blank=True)
    filter_heading = models.CharField(max_length=255, blank=True)
    filter_all_label = models.CharField(max_length=255, blank=True)
    empty_state_text = models.CharField(max_length=255, blank=True)

    def serve_preview(self, request, mode_name):
        from catalogs_cms.api import serialize_catalog_index_page

        lang = getattr(getattr(self, "locale", None), "language_code", "en")
        data = serialize_catalog_index_page(self, request, lang)

        return render(
            request,
            "catalogs_cms/astro_preview.html",
            {
                "preview_data": data,
                "preview_lang": lang,
                "astro_preview_url": settings.ASTRO_PREVIEW_URL,
            },
        )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("catalogs_eyebrow"),
                FieldPanel("catalogs_heading"),
                FieldPanel("catalogs_prev_aria"),
                FieldPanel("catalogs_next_aria"),
                FieldPanel("catalogs_dot_aria"),
                FieldPanel("filter_heading"),
                FieldPanel("filter_all_label"),
                FieldPanel("empty_state_text"),
            ],
            heading="Catalogs copy",
        ),
        InlinePanel("filter_categories", label="Categories"),
        InlinePanel("catalog_items", label="Catalogs"),
    ]


class CatalogFilterCategory(TranslatableMixin, Orderable):
    page = ParentalKey(
        "catalogs_cms.CatalogIndexPage",
        related_name="filter_categories",
        on_delete=models.CASCADE,
    )
    key = models.SlugField(max_length=120)
    label = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["translation_key", "locale"],
                name="unique_translation_key_locale_catalogs_cms_catalogfiltercategory",
            ),
            models.UniqueConstraint(
                fields=["page", "key"],
                name="catalogs_cms_catalogfiltercategory_unique_key_per_page",
            ),
        ]

    def clean(self):
        super().clean()
        if self.locale_id is None and self.page_id:
            self.locale_id = self.page.locale_id

    panels = [
        FieldPanel("key"),
        FieldPanel("label"),
    ]


class CatalogIndexItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "catalogs_cms.CatalogIndexPage",
        related_name="catalog_items",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=150)
    categories = models.JSONField(
        default=list,
        blank=True,
        help_text="Category keys (kebab-case) this catalog belongs to.",
    )
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    file_document = models.ForeignKey(
        "wagtaildocs.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Upload the PDF file to be downloaded from this catalog card.",
    )
    file_url = models.URLField(blank=True)

    def clean(self):
        super().clean()
        if self.locale_id is None and self.page_id:
            self.locale_id = self.page.locale_id

    panels = [
        FieldPanel("title"),
        FieldPanel("categories"),
        FieldPanel("image"),
        FieldPanel("file_document", heading="File Url"),
        FieldPanel("file_url"),
    ]
