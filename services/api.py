from django.http import JsonResponse

from services.models import ServicesPage
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


def _get_image_payload(image, request, alt_text=""):
    if not image:
        return {"url": "", "alt": _normalize_copy_text(alt_text)}

    image_url = image.file.url if getattr(image, "file", None) else ""
    image_url = _build_absolute_url(request, image_url)

    fallback_alt = ""
    for attr_name in ("alt", "alt_text"):
        value = getattr(image, attr_name, None)
        if value:
            fallback_alt = value
            break
    if not fallback_alt:
        fallback_alt = getattr(image, "title", "") or ""

    return {
        "url": image_url,
        "alt": _normalize_copy_text(alt_text) or _normalize_copy_text(fallback_alt),
    }


def _get_services_page_for_api(request):
    lang = _resolve_language(request)
    queryset = ServicesPage.objects.select_related("locale", "hero_image").prefetch_related(
        "service_items",
        "service_items__image",
    )
    return get_page_with_locale_fallback(queryset, request, lang)


def _normalize_body(body):
    if isinstance(body, list):
        normalized_body = []
        for paragraph in body:
            normalized = _normalize_copy_text(paragraph)
            if normalized:
                normalized_body.append(normalized)
        return normalized_body

    normalized_text = _normalize_copy_text(body)
    if not normalized_text:
        return []
    return [normalized_text]


def _get_services_payload(page, request):
    services = list(getattr(page, "service_items", []).all().order_by("sort_order", "pk"))
    payload = []
    for service in services:
        payload.append(
            {
                "key": _normalize_copy_text(getattr(service, "key", "")),
                "heading": _normalize_copy_text(getattr(service, "heading", "")),
                "subtitle": _normalize_copy_text(getattr(service, "subtitle", "")),
                "body": _normalize_body(getattr(service, "body", [])),
                "image": _get_image_payload(
                    getattr(service, "image", None),
                    request,
                    getattr(service, "image_alt", ""),
                ),
            }
        )
    return payload


def serialize_services_page(page, request, requested_lang=None):
    requested_lang = requested_lang or _resolve_language(request)
    response_locale = _normalize_locale_code(
        getattr(getattr(page, "locale", None), "language_code", requested_lang)
    )

    seo_title = _normalize_copy_text(getattr(page, "seo_title", "")) or _normalize_copy_text(
        getattr(page, "title", "")
    )
    meta = {
        "seo_title": seo_title,
        "search_description": _normalize_copy_text(getattr(page, "search_description", "")),
    }
    translations = build_translations_map(page)
    if translations:
        meta["translations"] = translations

    return {
        "type": "services.ServicesPage",
        "title": _normalize_copy_text(getattr(page, "title", "")),
        "locale": response_locale,
        "meta": meta,
        "fields": {
            "hero_image": _get_image_payload(
                getattr(page, "hero_image", None),
                request,
                getattr(page, "hero_image_alt", ""),
            ),
            "intro_eyebrow": _normalize_copy_text(getattr(page, "intro_eyebrow", "")),
            "intro_heading": _normalize_copy_text(getattr(page, "intro_heading", "")),
            "intro_text": _normalize_copy_text(getattr(page, "intro_text", "")),
            "services": _get_services_payload(page, request),
        },
    }


def services_page_api(request):
    requested_lang = _resolve_language(request)
    page = _get_services_page_for_api(request)

    if page is None:
        return JsonResponse(
            {
                "type": "services.ServicesPage",
                "title": "",
                "locale": requested_lang,
                "meta": {"seo_title": "", "search_description": ""},
                "fields": {
                    "hero_image": {"url": "", "alt": ""},
                    "intro_eyebrow": "",
                    "intro_heading": "",
                    "intro_text": "",
                    "services": [],
                },
            }
        )

    return JsonResponse(serialize_services_page(page, request, requested_lang))
