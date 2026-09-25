from django.conf import settings
from django.shortcuts import render

from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, Page, TranslatableMixin


class ServicesPage(Page):
    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    hero_image_alt = models.CharField(max_length=255, blank=True)
    intro_eyebrow = models.CharField(max_length=255, blank=True)
    intro_heading = models.CharField(max_length=255, blank=True)
    intro_text = models.TextField(blank=True)

    def serve_preview(self, request, mode_name):
        from services.api import serialize_services_page

        lang = getattr(getattr(self, "locale", None), "language_code", "en")
        data = serialize_services_page(self, request, lang)

        return render(
            request,
            "services/astro_preview.html",
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
                FieldPanel("intro_eyebrow"),
                FieldPanel("intro_heading"),
                FieldPanel("intro_text"),
                FieldPanel("search_description"),
            ],
            heading="Services copy",
        ),
        InlinePanel("service_items", label="Services"),
    ]


class ServiceItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "services.ServicesPage",
        related_name="service_items",
        on_delete=models.CASCADE,
    )
    key = models.SlugField(max_length=80)
    heading = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    body = models.JSONField(default=list, blank=True)
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
        FieldPanel("key"),
        FieldPanel("heading"),
        FieldPanel("subtitle"),
        FieldPanel("body"),
        FieldPanel("image"),
        FieldPanel("image_alt"),
    ]

    def __str__(self):
        heading = (self.heading or "").strip()
        key = (self.key or "").strip()
        if heading and key:
            return f"{heading} ({key})"
        return heading or key or f"Service #{self.pk}"
