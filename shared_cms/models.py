from django.db import models
from django.core.exceptions import ValidationError
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Locale, Orderable, TranslatableMixin
from wagtail.snippets.models import register_snippet


def _effective_locale_id(instance):
    if instance.locale_id is not None:
        return instance.locale_id

    default_locale = Locale.get_default()
    return default_locale.pk if default_locale is not None else None


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

        locale_id = _effective_locale_id(self)
        if locale_id is None:
            return

        duplicate_exists = DirectContactBlock.objects.filter(locale_id=locale_id).exclude(pk=self.pk).exists()
        if duplicate_exists:
            raise ValidationError("Only one DirectContactBlock is allowed per locale.")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["translation_key", "locale"],
                name="unique_translation_key_locale_shared_cms_directcontactblock",
            ),
            models.UniqueConstraint(
                fields=["locale"],
                name="unique_directcontactblock_locale",
            ),
        ]


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


@register_snippet
class BrandsHeaderBlock(TranslatableMixin, ClusterableModel):
    title = models.CharField(max_length=255, default="Brands header")

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("title"),
            ],
            heading="Brands header content",
        ),
        InlinePanel("brand_logo_items", label="Brand logos"),
    ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()

        locale_id = _effective_locale_id(self)
        if locale_id is None:
            return

        duplicate_exists = BrandsHeaderBlock.objects.filter(locale_id=locale_id).exclude(pk=self.pk).exists()
        if duplicate_exists:
            raise ValidationError("Only one BrandsHeaderBlock is allowed per locale.")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["translation_key", "locale"],
                name="unique_translation_key_locale_shared_cms_brandsheaderblock",
            ),
            models.UniqueConstraint(
                fields=["locale"],
                name="unique_brandsheaderblock_locale",
            ),
        ]


class BrandsHeaderLogoItem(TranslatableMixin, Orderable):
    block = ParentalKey(
        "shared_cms.BrandsHeaderBlock",
        related_name="brand_logo_items",
        on_delete=models.CASCADE,
    )
    key = models.CharField(max_length=100)
    placeholder_text = models.CharField(max_length=255, blank=True)
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    panels = [
        FieldPanel("key"),
        FieldPanel("placeholder_text"),
        FieldPanel("image"),
    ]
