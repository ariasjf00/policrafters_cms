from django.http import JsonResponse

from contact_cms.models import ContactPage
from shared_cms.api_utils import (
    build_absolute_asset_url,
    build_translations_map,
    get_page_with_locale_fallback,
    resolve_request_language,
)


_resolve_language = resolve_request_language


def _normalize_copy_text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return ""
    return " ".join(str(value).split())


def _normalize_locale_code(locale_code):
    locale = str(locale_code or "").lower()
    if locale.startswith("es"):
        return "es"
    return "en"


def _build_absolute_url(request, value):
    url = _normalize_copy_text(value)
    return build_absolute_asset_url(request, url)


def _get_image_payload(image, request):
    if not image:
        return {"url": "", "alt": ""}

    image_url = image.file.url if getattr(image, "file", None) else ""
    image_url = _build_absolute_url(request, image_url)

    alt_text = ""
    for attr_name in ("alt", "alt_text"):
        value = getattr(image, attr_name, None)
        if value:
            alt_text = value
            break

    if not alt_text:
        alt_text = getattr(image, "title", "") or ""

    return {
        "url": image_url,
        "alt": alt_text,
    }


def _get_page_for_api(request):
    lang = _resolve_language(request)
    queryset = ContactPage.objects.select_related("locale").prefetch_related("location_items")
    return get_page_with_locale_fallback(queryset, request, lang)


def _get_copy(page):
    return {
        "heading": _normalize_copy_text(getattr(page, "heading", "")),
        "intro": _normalize_copy_text(getattr(page, "intro", "")),
        "phone_label": _normalize_copy_text(getattr(page, "phone_label", "")),
        "email_label": _normalize_copy_text(getattr(page, "email_label", "")),
        "banner_eyebrow": _normalize_copy_text(getattr(page, "banner_eyebrow", "")),
        "banner_heading": _normalize_copy_text(getattr(page, "banner_heading", "")),
        "project_button_label": _normalize_copy_text(getattr(page, "project_button_label", "")),
        "locations_heading": _normalize_copy_text(getattr(page, "locations_heading", "")),
        "locations_aria": _normalize_copy_text(getattr(page, "locations_aria", "")),
        "learn_more": _normalize_copy_text(getattr(page, "learn_more", "")),
    }


def _empty_contact_page_payload(requested_lang):
    return {
        "type": "contact_cms.ContactPage",
        "title": "",
        "locale": requested_lang,
        "meta": {
            "seo_title": "",
            "search_description": "",
        },
        "fields": {
            "copy": {
                "heading": "",
                "intro": "",
                "phone_label": "",
                "email_label": "",
                "banner_eyebrow": "",
                "banner_heading": "",
                "project_button_label": "",
                "locations_heading": "",
                "locations_aria": "",
                "learn_more": "",
            },
            "contact": {
                "phone_display": "",
                "phone_href": None,
                "email": "",
                "url_contact": "",
            },
            "banner_image": {"url": "", "alt": ""},
            "locations": [],
        },
    }


def serialize_contact_page(page, request, requested_lang=None):
    requested_lang = requested_lang or _resolve_language(request)
    response_locale = _normalize_locale_code(
        getattr(getattr(page, "locale", None), "language_code", requested_lang)
    )

    locations = []
    items = getattr(page, "location_items", None)
    if items is not None and hasattr(items, "all"):
        for item in items.all():
            locations.append(
                {
                    "name": _normalize_copy_text(getattr(item, "name", "")),
                    "address_label": _normalize_copy_text(getattr(item, "address_label", "")),
                    "street": _normalize_copy_text(getattr(item, "street", "")),
                    "city": _normalize_copy_text(getattr(item, "city", "")),
                    "url": _normalize_copy_text(getattr(item, "url", "")),
                    "image": _get_image_payload(getattr(item, "image", None), request),
                }
            )

    seo_title = _normalize_copy_text(getattr(page, "seo_title", "")) or _normalize_copy_text(
        getattr(page, "title", "")
    )
    search_description = _normalize_copy_text(
        getattr(page, "search_description", "")
    ) or _normalize_copy_text(getattr(page, "intro", ""))
    meta = {
        "seo_title": seo_title,
        "search_description": search_description,
    }
    translations = build_translations_map(page)
    if translations:
        meta["translations"] = translations

    return {
        "type": "contact_cms.ContactPage",
        "title": _normalize_copy_text(getattr(page, "title", "")),
        "locale": response_locale,
        "meta": meta,
        "fields": {
            "copy": _get_copy(page),
            "contact": {
                "phone_display": _normalize_copy_text(getattr(page, "phone_display", "")),
                "phone_href": _normalize_copy_text(getattr(page, "phone_href", "")) or None,
                "email": _normalize_copy_text(getattr(page, "email", "")),
                "url_contact": _normalize_copy_text(getattr(page, "url_contact", "")) or None,
            },
            "banner_image": _get_image_payload(getattr(page, "banner_image", None), request),
            "locations": locations,
        },
    }


def contact_page_api(request):
    requested_lang = _resolve_language(request)
    page = _get_page_for_api(request)

    if page is None:
        return JsonResponse(_empty_contact_page_payload(requested_lang))

    return JsonResponse(serialize_contact_page(page, request, requested_lang))
