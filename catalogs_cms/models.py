from django.db import models

from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, Page, TranslatableMixin


class CatalogIndexPage(Page):
    catalogs_eyebrow = models.CharField(max_length=255, blank=True)
    catalogs_heading = models.CharField(max_length=255, blank=True)
    catalogs_prev_aria = models.CharField(max_length=255, blank=True)
    catalogs_next_aria = models.CharField(max_length=255, blank=True)
    catalogs_dot_aria = models.CharField(max_length=255, blank=True)

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("catalogs_eyebrow"),
                FieldPanel("catalogs_heading"),
                FieldPanel("catalogs_prev_aria"),
                FieldPanel("catalogs_next_aria"),
                FieldPanel("catalogs_dot_aria"),
            ],
            heading="Catalogs copy",
        ),
        InlinePanel("catalog_items", label="Catalogs"),
    ]


class CatalogIndexItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "catalogs_cms.CatalogIndexPage",
        related_name="catalog_items",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=150)
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

    panels = [
        FieldPanel("title"),
        FieldPanel("image"),
        FieldPanel("file_document", heading="File Url"),
        FieldPanel("file_url"),
    ]
