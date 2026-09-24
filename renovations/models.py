from django.conf import settings
from django.shortcuts import render

from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, Page, TranslatableMixin


class RenovationIndexPage(Page):
    hero_title = models.CharField(max_length=255, blank=True)
    intro_text = models.TextField(blank=True)
    empty_state_text = models.CharField(max_length=255, blank=True)

    def serve_preview(self, request, mode_name):
        from renovations.api import serialize_renovation_index_page

        lang = getattr(getattr(self, "locale", None), "language_code", "en")
        data = serialize_renovation_index_page(self, request, lang)

        return render(
            request,
            "renovations/astro_preview.html",
            {
                "preview_data": data,
                "preview_lang": lang,
                "astro_preview_url": settings.ASTRO_PREVIEW_URL,
            },
        )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("hero_title"),
                FieldPanel("intro_text"),
                FieldPanel("empty_state_text"),
                FieldPanel("search_description"),
            ],
            heading="Renovations copy",
        ),
        InlinePanel("category_items", label="Categories"),
        InlinePanel("type_items", label="Types"),
        InlinePanel("product_items", label="Products"),
    ]


class RenovationCategoryItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "renovations.RenovationIndexPage",
        related_name="category_items",
        on_delete=models.CASCADE,
    )
    key = models.SlugField(max_length=80)
    label = models.CharField(max_length=120)
    show_type_filters = models.BooleanField(default=True)

    def clean(self):
        super().clean()
        if self.locale_id is None and self.page_id:
            self.locale_id = self.page.locale_id

    panels = [
        FieldPanel("key"),
        FieldPanel("label"),
        FieldPanel("show_type_filters"),
    ]

    def __str__(self):
        label = (self.label or "").strip()
        key = (self.key or "").strip()
        if label and key:
            return f"{label} ({key})"
        return label or key or f"Category #{self.pk}"


class RenovationTypeItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "renovations.RenovationIndexPage",
        related_name="type_items",
        on_delete=models.CASCADE,
    )
    category_key = models.SlugField(max_length=80, blank=True)
    key = models.SlugField(max_length=80)
    label = models.CharField(max_length=120)

    def clean(self):
        super().clean()
        if self.locale_id is None and self.page_id:
            self.locale_id = self.page.locale_id

    panels = [
        FieldPanel("category_key"),
        FieldPanel("key"),
        FieldPanel("label"),
    ]

    def __str__(self):
        label = (self.label or "").strip()
        key = (self.key or "").strip()
        if label and key:
            return f"{label} ({key})"
        return label or key or f"Type #{self.pk}"


class RenovationProductItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "renovations.RenovationIndexPage",
        related_name="product_items",
        on_delete=models.CASCADE,
    )
    category_key = models.SlugField(max_length=80, blank=True)
    type_key = models.SlugField(max_length=80, blank=True)
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150)
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    image_alt = models.CharField(max_length=255, blank=True)

    def clean(self):
        super().clean()
        if self.locale_id is None and self.page_id:
            self.locale_id = self.page.locale_id

    panels = [
        FieldPanel("category_key"),
        FieldPanel("type_key"),
        FieldPanel("title"),
        FieldPanel("slug"),
        FieldPanel("image"),
        FieldPanel("image_alt"),
    ]
