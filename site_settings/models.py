from django.core.exceptions import ValidationError
from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting


@register_setting
class SiteSettings(BaseGenericSetting):
    legal_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True, null=True)
    addresses = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "JSON list of address objects with street, city, region, postal_code, "
            "and country."
        ),
    )
    opening_hours = models.JSONField(
        default=list,
        blank=True,
        help_text='Use Schema.org values, for example ["Mo-Fr 08:00-17:00"].',
    )
    area_served = models.JSONField(
        default=list,
        blank=True,
        help_text="JSON list of service-area names.",
    )
    license_number = models.CharField(max_length=120, blank=True)
    certifications = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "JSON list of objects with name and optional issuer and url values."
        ),
    )
    social_links = models.JSONField(
        default=list,
        blank=True,
        help_text="JSON list of social profile URLs.",
    )
    logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    seo_title_en = models.CharField(max_length=255, blank=True)
    seo_title_es = models.CharField(max_length=255, blank=True)
    search_description_en = models.TextField(blank=True)
    search_description_es = models.TextField(blank=True)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("legal_name"),
                FieldPanel("phone"),
                FieldPanel("email"),
                FieldPanel("addresses"),
                FieldPanel("opening_hours"),
                FieldPanel("area_served"),
                FieldPanel("license_number"),
                FieldPanel("certifications"),
                FieldPanel("social_links"),
                FieldPanel("logo"),
            ],
            heading="Company information",
        ),
        MultiFieldPanel(
            [
                FieldPanel("seo_title_en"),
                FieldPanel("search_description_en"),
            ],
            heading="English SEO metadata",
        ),
        MultiFieldPanel(
            [
                FieldPanel("seo_title_es"),
                FieldPanel("search_description_es"),
            ],
            heading="Spanish SEO metadata",
        ),
    ]

    class Meta:
        verbose_name = "Site settings"

    def clean(self):
        super().clean()
        errors = {}

        for field_name in ("opening_hours", "area_served", "social_links"):
            values = getattr(self, field_name)
            if not isinstance(values, list) or any(
                not isinstance(value, str) for value in values
            ):
                errors[field_name] = "Enter a list of text values."

        for field_name, required_keys in (
            ("addresses", ("street", "city", "region", "postal_code", "country")),
            ("certifications", ("name",)),
        ):
            values = getattr(self, field_name)
            if not isinstance(values, list):
                errors[field_name] = "Enter a list of objects."
                continue

            for value in values:
                if not isinstance(value, dict) or any(
                    not isinstance(value.get(key), str) for key in required_keys
                ):
                    errors[field_name] = (
                        "Each item must be an object with the required text fields."
                    )
                    break

        if isinstance(self.certifications, list):
            for certification in self.certifications:
                if not isinstance(certification, dict):
                    continue
                for field_name in ("issuer", "url"):
                    value = certification.get(field_name)
                    if value is not None and not isinstance(value, str):
                        errors["certifications"] = (
                            "Certification issuer and URL must be text or null."
                        )
                        break

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return str(self._meta.verbose_name)
