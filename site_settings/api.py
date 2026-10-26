from django.http import JsonResponse

from shared_cms.api_utils import resolve_request_language, serialize_image_payload
from site_settings.models import SiteSettings


def site_settings_api(request):
    locale = resolve_request_language(request)
    settings = SiteSettings.objects.select_related("logo").first() or SiteSettings()
    seo_suffix = "es" if locale == "es" else "en"

    return JsonResponse(
        {
            "type": "site.SiteSettings",
            "title": str(settings),
            "locale": locale,
            "meta": {
                "seo_title": getattr(settings, f"seo_title_{seo_suffix}"),
                "search_description": getattr(
                    settings,
                    f"search_description_{seo_suffix}",
                ),
            },
            "fields": {
                "legal_name": settings.legal_name,
                "phone": settings.phone,
                "email": settings.email or None,
                "addresses": settings.addresses,
                "opening_hours": settings.opening_hours,
                "area_served": settings.area_served,
                "license_number": settings.license_number,
                "certifications": settings.certifications,
                "social_links": settings.social_links,
                "logo": serialize_image_payload(settings.logo, request),
            },
        }
    )
