from django.conf import settings
from django.db import models
from django.shortcuts import render

from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, Page, TranslatableMixin


class WhyPolicraftersPage(Page):
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
    intro_body = models.JSONField(default=list, blank=True)

    why_eyebrow = models.CharField(max_length=255, blank=True)
    why_heading = models.CharField(max_length=255, blank=True)

    certifications_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    certifications_image_alt = models.CharField(max_length=255, blank=True)
    certifications_eyebrow = models.CharField(max_length=255, blank=True)
    certifications_heading = models.CharField(max_length=255, blank=True)
    certifications_body = models.JSONField(default=list, blank=True)

    identity_eyebrow = models.CharField(max_length=255, blank=True)
    identity_heading = models.CharField(max_length=255, blank=True)

    partners_eyebrow = models.CharField(max_length=255, blank=True)
    partners_heading = models.CharField(max_length=255, blank=True)
    partners_intro = models.TextField(blank=True)

    def serve_preview(self, request, mode_name):
        from why_policrafters.api import serialize_why_policrafters_page

        lang = getattr(getattr(self, "locale", None), "language_code", "en")
        data = serialize_why_policrafters_page(self, request, lang)

        return render(
            request,
            "why_policrafters/astro_preview.html",
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
                FieldPanel("intro_body"),
                FieldPanel("search_description"),
            ],
            heading="Hero & intro",
        ),
        MultiFieldPanel(
            [
                FieldPanel("why_eyebrow"),
                FieldPanel("why_heading"),
            ],
            heading="Why choose us",
        ),
        InlinePanel("why_items", label="Why items"),
        MultiFieldPanel(
            [
                FieldPanel("certifications_image"),
                FieldPanel("certifications_image_alt"),
                FieldPanel("certifications_eyebrow"),
                FieldPanel("certifications_heading"),
                FieldPanel("certifications_body"),
            ],
            heading="Certifications",
        ),
        InlinePanel("issuers", label="Issuers"),
        MultiFieldPanel(
            [
                FieldPanel("identity_eyebrow"),
                FieldPanel("identity_heading"),
            ],
            heading="Corporate identity",
        ),
        InlinePanel("identity_items", label="Identity items"),
        MultiFieldPanel(
            [
                FieldPanel("partners_eyebrow"),
                FieldPanel("partners_heading"),
                FieldPanel("partners_intro"),
            ],
            heading="Partners",
        ),
        InlinePanel("partners", label="Partners"),
    ]


class WhyItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "why_policrafters.WhyPolicraftersPage",
        related_name="why_items",
        on_delete=models.CASCADE,
    )
    key = models.SlugField(max_length=120)
    heading = models.CharField(max_length=255)
    body = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["translation_key", "locale"],
                name="unique_translation_key_locale_why_policrafters_whyitem",
            ),
            models.UniqueConstraint(
                fields=["page", "key"],
                name="why_policrafters_whyitem_unique_key_per_page",
            ),
        ]

    def clean(self):
        super().clean()
        if self.locale_id is None and self.page_id:
            self.locale_id = self.page.locale_id

    panels = [
        FieldPanel("key"),
        FieldPanel("heading"),
        FieldPanel("body"),
    ]


class CertificationIssuer(TranslatableMixin, ClusterableModel, Orderable):
    page = ParentalKey(
        "why_policrafters.WhyPolicraftersPage",
        related_name="issuers",
        on_delete=models.CASCADE,
    )
    key = models.SlugField(max_length=120)
    logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    logo_alt = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["translation_key", "locale"],
                name="unique_translation_key_locale_why_policrafters_certificationissuer",
            ),
            models.UniqueConstraint(
                fields=["page", "key"],
                name="why_policrafters_certificationissuer_unique_key_per_page",
            ),
        ]

    def clean(self):
        super().clean()
        if self.locale_id is None and self.page_id:
            self.locale_id = self.page.locale_id

    panels = [
        FieldPanel("key"),
        FieldPanel("logo"),
        FieldPanel("logo_alt"),
        InlinePanel("licenses", label="Licenses"),
    ]


class IssuerLicense(TranslatableMixin, Orderable):
    page = ParentalKey(
        "why_policrafters.CertificationIssuer",
        related_name="licenses",
        on_delete=models.CASCADE,
    )
    label = models.CharField(max_length=255, blank=True)
    number = models.CharField(max_length=255, blank=True)
    caption = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["translation_key", "locale"],
                name="unique_translation_key_locale_why_policrafters_issuerlicense",
            ),
        ]

    def clean(self):
        super().clean()
        if self.locale_id is None and self.page_id:
            self.locale_id = self.page.locale_id

    panels = [
        FieldPanel("label"),
        FieldPanel("number"),
        FieldPanel("caption"),
    ]


class IdentityItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "why_policrafters.WhyPolicraftersPage",
        related_name="identity_items",
        on_delete=models.CASCADE,
    )
    key = models.SlugField(max_length=120)
    heading = models.CharField(max_length=255)
    body = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["translation_key", "locale"],
                name="unique_translation_key_locale_why_policrafters_identityitem",
            ),
            models.UniqueConstraint(
                fields=["page", "key"],
                name="why_policrafters_identityitem_unique_key_per_page",
            ),
        ]

    def clean(self):
        super().clean()
        if self.locale_id is None and self.page_id:
            self.locale_id = self.page.locale_id

    panels = [
        FieldPanel("key"),
        FieldPanel("heading"),
        FieldPanel("body"),
    ]


class PartnerItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "why_policrafters.WhyPolicraftersPage",
        related_name="partners",
        on_delete=models.CASCADE,
    )
    key = models.SlugField(max_length=120)
    logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    logo_alt = models.CharField(max_length=255, blank=True)
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    image_alt = models.CharField(max_length=255, blank=True)
    body = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["translation_key", "locale"],
                name="unique_translation_key_locale_why_policrafters_partneritem",
            ),
            models.UniqueConstraint(
                fields=["page", "key"],
                name="why_policrafters_partneritem_unique_key_per_page",
            ),
        ]

    def clean(self):
        super().clean()
        if self.locale_id is None and self.page_id:
            self.locale_id = self.page.locale_id

    panels = [
        FieldPanel("key"),
        FieldPanel("logo"),
        FieldPanel("logo_alt"),
        FieldPanel("image"),
        FieldPanel("image_alt"),
        FieldPanel("body"),
    ]
