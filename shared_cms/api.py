from django.http import JsonResponse

from shared_cms.models import FooterBlock
from shared_cms.api_utils import normalize_supported_language, resolve_request_language


def _get_footer_block(locale):
    queryset = FooterBlock.objects.select_related("locale").prefetch_related(
        "navigation_links",
        "residential_links",
        "commercial_links",
        "social_links",
    )
    block = queryset.filter(locale__language_code=locale).order_by("-pk").first()
    if block is None and locale != "en":
        block = queryset.filter(locale__language_code="en").order_by("-pk").first()
    if block is None:
        block = queryset.order_by("-pk").first()
    return block


def _serialize_footer_links(items, include_icon=False):
    payload = []
    for item in items.all().order_by("sort_order", "pk"):
        link = {
            "key": item.key,
            "label": item.label,
            "href": item.href,
            "localizedPath": item.localized_path,
        }
        if include_icon:
            link["icon"] = item.icon
        payload.append(link)
    return payload


def _serialize_footer(block, requested_locale):
    response_locale = normalize_supported_language(
        getattr(getattr(block, "locale", None), "language_code", requested_locale)
    ) or requested_locale
    return {
        "type": "site.Footer",
        "title": block.title,
        "locale": response_locale,
        "fields": {
            "copy": _serialize_footer_copy(block),
            "navigation_links": _serialize_footer_links(block.navigation_links),
            "residential_links": _serialize_footer_links(block.residential_links),
            "commercial_links": _serialize_footer_links(block.commercial_links),
            "social_links": _serialize_footer_links(block.social_links, include_icon=True),
        },
    }


def _serialize_footer_copy(block=None):
    copy_fields = (
        "blurb_1",
        "blurb_2",
        "phone_label",
        "residential_label",
        "email_label",
        "commercial_label",
        "address_label",
        "social_label",
        "copyright_text",
    )
    return {
        field: getattr(block, field, "") if block is not None else ""
        for field in copy_fields
    }


def footer_api(request):
    requested_locale = resolve_request_language(request)
    block = _get_footer_block(requested_locale)

    if block is None:
        data = {
            "type": "site.Footer",
            "title": "",
            "locale": requested_locale,
            "fields": {
                "copy": _serialize_footer_copy(),
                "navigation_links": [],
                "residential_links": [],
                "commercial_links": [],
                "social_links": [],
            },
        }
    else:
        data = _serialize_footer(block, requested_locale)

    response = JsonResponse(data)
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response
