from django.db import models
from django.core.exceptions import ValidationError
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, TranslatableMixin
from wagtail.snippets.models import register_snippet


@register_snippet
class DirectContactBlock(TranslatableMixin, ClusterableModel):
    title = models.CharField(max_length=255, default="Direct contact")
    contact_heading = models.CharField(max_length=255, blank=True)
    contact_cta = models.CharField(max_length=120, blank=True)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("title"),
                FieldPanel("contact_heading"),
                FieldPanel("contact_cta"),
            ],
            heading="Direct contact copy",
        ),
        InlinePanel("contact_link_items", label="Contact links"),
    ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()

        if self.locale_id is None:
            return

        duplicate_exists = DirectContactBlock.objects.filter(locale_id=self.locale_id).exclude(pk=self.pk).exists()
        if duplicate_exists:
            raise ValidationError(
                {
                    "locale": "Only one DirectContactBlock is allowed per locale.",
                }
            )


class DirectContactLinkItem(TranslatableMixin, Orderable):
    block = ParentalKey(
        "shared_cms.DirectContactBlock",
        related_name="contact_link_items",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    url = models.URLField()

    panels = [
        FieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("url"),
    ]
