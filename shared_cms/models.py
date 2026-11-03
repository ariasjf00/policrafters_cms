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


@register_snippet
class FooterBlock(TranslatableMixin, ClusterableModel):
    title = models.CharField(max_length=255, default="Footer")
    blurb_1 = models.TextField(blank=True)
    blurb_2 = models.TextField(blank=True)
    phone_label = models.CharField(max_length=255, blank=True)
    residential_label = models.CharField(max_length=255, blank=True)
    email_label = models.CharField(max_length=255, blank=True)
    commercial_label = models.CharField(max_length=255, blank=True)
    address_label = models.CharField(max_length=255, blank=True)
    social_label = models.CharField(max_length=255, blank=True)
    copyright_text = models.CharField(max_length=255, blank=True)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("title"),
                FieldPanel("blurb_1"),
                FieldPanel("blurb_2"),
                FieldPanel("phone_label"),
                FieldPanel("residential_label"),
                FieldPanel("email_label"),
                FieldPanel("commercial_label"),
                FieldPanel("address_label"),
                FieldPanel("social_label"),
                FieldPanel("copyright_text"),
            ],
            heading="Footer content",
        ),
        InlinePanel("navigation_links", label="Navigation links"),
        InlinePanel("residential_links", label="Residential links"),
        InlinePanel("commercial_links", label="Commercial links"),
        InlinePanel("social_links", label="Social links"),
    ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()

        locale_id = _effective_locale_id(self)
        if locale_id is None:
            return

        duplicate_exists = FooterBlock.objects.filter(locale_id=locale_id).exclude(pk=self.pk).exists()
        if duplicate_exists:
            raise ValidationError("Only one FooterBlock is allowed per locale.")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["translation_key", "locale"],
                name="unique_translation_key_locale_shared_cms_footerblock",
            ),
            models.UniqueConstraint(
                fields=["locale"],
                name="unique_footerblock_locale",
            ),
        ]


class FooterLinkFields(models.Model):
    key = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    href = models.CharField(max_length=1000)
    localized_path = models.CharField(max_length=1000, blank=True)

    panels = [
        FieldPanel("key"),
        FieldPanel("label"),
        FieldPanel("href"),
        FieldPanel("localized_path"),
    ]

    class Meta:
        abstract = True


class FooterNavigationLink(TranslatableMixin, Orderable, FooterLinkFields):
    footer = ParentalKey(
        "shared_cms.FooterBlock",
        related_name="navigation_links",
        on_delete=models.CASCADE,
    )


class FooterResidentialLink(TranslatableMixin, Orderable, FooterLinkFields):
    footer = ParentalKey(
        "shared_cms.FooterBlock",
        related_name="residential_links",
        on_delete=models.CASCADE,
    )


class FooterCommercialLink(TranslatableMixin, Orderable, FooterLinkFields):
    footer = ParentalKey(
        "shared_cms.FooterBlock",
        related_name="commercial_links",
        on_delete=models.CASCADE,
    )


class FooterSocialLink(TranslatableMixin, Orderable, FooterLinkFields):
    footer = ParentalKey(
        "shared_cms.FooterBlock",
        related_name="social_links",
        on_delete=models.CASCADE,
    )
    icon = models.CharField(max_length=100)

    panels = FooterLinkFields.panels + [FieldPanel("icon")]
