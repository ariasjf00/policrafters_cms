from django.db import models

from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, Page, TranslatableMixin


class ContactPage(Page):
    heading = models.CharField(max_length=255, blank=True)
    intro = models.TextField(blank=True)
    phone_label = models.CharField(max_length=120, blank=True)
    email_label = models.CharField(max_length=120, blank=True)
    locations_heading = models.CharField(max_length=255, blank=True)
    locations_aria = models.CharField(max_length=255, blank=True)
    learn_more = models.CharField(max_length=120, blank=True)

    phone_display = models.CharField(max_length=120, blank=True)
    phone_href = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("heading"),
                FieldPanel("intro"),
                FieldPanel("phone_label"),
                FieldPanel("email_label"),
                FieldPanel("locations_heading"),
                FieldPanel("locations_aria"),
                FieldPanel("learn_more"),
            ],
            heading="Copy",
        ),
        MultiFieldPanel(
            [
                FieldPanel("phone_display"),
                FieldPanel("phone_href"),
                FieldPanel("email"),
            ],
            heading="Contact",
        ),
        InlinePanel("location_items", label="Locations"),
    ]


class ContactLocationItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "contact_cms.ContactPage",
        related_name="location_items",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=150)
    address_label = models.CharField(max_length=120, blank=True)
    street = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True)
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("address_label"),
        FieldPanel("street"),
        FieldPanel("city"),
        FieldPanel("url"),
        FieldPanel("image"),
    ]
