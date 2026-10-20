from django.http import JsonResponse

from shared_cms.api_utils import build_translations_map, get_page_with_locale_fallback, resolve_request_language
from warranty_cms.models import WarrantyPage


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


def _get_warranty_page_for_api(request):
    lang = _resolve_language(request)
    queryset = WarrantyPage.objects.select_related("locale").prefetch_related("sections__items")
    return get_page_with_locale_fallback(queryset, request, lang)


def _empty_warranty_page_payload(requested_lang):
    return {
        "type": "warranty.WarrantyPage",
        "title": "",
        "locale": requested_lang,
        "meta": {
            "seo_title": "",
            "search_description": "",
        },
        "fields": {
            "intro_heading": "",
            "intro_body": "",
            "sections": [],
        },
    }


def serialize_warranty_page(page, request, requested_lang=None):
    requested_lang = requested_lang or _resolve_language(request)
    response_locale = _normalize_locale_code(
        getattr(getattr(page, "locale", None), "language_code", requested_lang)
    )

    sections = []
    section_qs = getattr(page, "sections", None)
    if section_qs is not None and hasattr(section_qs, "all"):
        for section in section_qs.all().order_by("sort_order", "pk"):
            items = []
            for item in section.items.all().order_by("sort_order", "pk"):
                items.append(
                    {
                        "label": _normalize_copy_text(getattr(item, "label", "")),
                        "text": _normalize_copy_text(getattr(item, "text", "")),
                    }
                )

            column = _normalize_copy_text(getattr(section, "column", "")).lower()
            if column not in {"left", "right"}:
                column = "left" if section.pk and section.pk % 2 == 0 else "right"

            sections.append(
                {
                    "key": _normalize_copy_text(getattr(section, "key", "")),
                    "title": _normalize_copy_text(getattr(section, "title", "")),
                    "column": column,
                    "intro": _normalize_copy_text(getattr(section, "intro", "")),
                    "items": items,
                }
            )

    seo_title = _normalize_copy_text(getattr(page, "seo_title", "")) or _normalize_copy_text(
        getattr(page, "title", "")
    )
    search_description = _normalize_copy_text(
        getattr(page, "search_description", "")
    ) or _normalize_copy_text(getattr(page, "intro_body", ""))
    meta = {
        "seo_title": seo_title,
        "search_description": search_description,
    }
    translations = build_translations_map(page)
    if translations:
        meta["translations"] = translations

    return {
        "type": "warranty.WarrantyPage",
        "title": _normalize_copy_text(getattr(page, "title", "")),
        "locale": response_locale,
        "meta": meta,
        "fields": {
            "intro_heading": _normalize_copy_text(getattr(page, "intro_heading", "")),
            "intro_body": _normalize_copy_text(getattr(page, "intro_body", "")),
            "sections": sections,
        },
    }


def warranty_page_api(request):
    requested_lang = _resolve_language(request)
    page = _get_warranty_page_for_api(request)

    if page is None:
        return JsonResponse(_empty_warranty_page_payload(requested_lang))

    return JsonResponse(serialize_warranty_page(page, request, requested_lang))
