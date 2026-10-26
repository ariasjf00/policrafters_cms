from django.http import JsonResponse

from catalogs_cms.models import CatalogIndexPage
from shared_cms.api_utils import (
    build_absolute_asset_url,
    build_translations_map,
    get_page_with_locale_fallback,
    resolve_request_language,
    serialize_image_payload as _get_image_payload,
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


def _get_page_for_api(request):
    lang = _resolve_language(request)
    queryset = CatalogIndexPage.objects.select_related("locale").prefetch_related(
        "catalog_items",
        "catalog_items__image",
        "catalog_items__file_document",
        "filter_categories",
    )
    return get_page_with_locale_fallback(queryset, request, lang)


def _get_copy(page):
    return {
        "catalogs_eyebrow": _normalize_copy_text(getattr(page, "catalogs_eyebrow", "")),
        "catalogs_heading": _normalize_copy_text(getattr(page, "catalogs_heading", "")),
        "catalogs_prev_aria": _normalize_copy_text(getattr(page, "catalogs_prev_aria", "")),
        "catalogs_next_aria": _normalize_copy_text(getattr(page, "catalogs_next_aria", "")),
        "catalogs_dot_aria": _normalize_copy_text(getattr(page, "catalogs_dot_aria", "")),
        "filter_heading": _normalize_copy_text(getattr(page, "filter_heading", "")),
        "filter_all_label": _normalize_copy_text(getattr(page, "filter_all_label", "")),
        "empty_state_text": _normalize_copy_text(getattr(page, "empty_state_text", "")),
    }


def _get_catalog_download_url(item, request):
    document = getattr(item, "file_document", None)
    if document is not None and getattr(document, "file", None):
        return _build_absolute_url(request, document.file.url)

    return _normalize_copy_text(getattr(item, "file_url", "")) or None


def _normalize_category_keys(value):
    if not isinstance(value, list):
        return []

    keys = []
    for entry in value:
        key = _normalize_copy_text(entry)
        if key:
            keys.append(key)
    return keys


def _get_categories_payload(page):
    categories = []
    category_items = getattr(page, "filter_categories", None)
    if category_items is not None and hasattr(category_items, "all"):
        for item in category_items.all().order_by("sort_order", "pk"):
            categories.append(
                {
                    "key": _normalize_copy_text(getattr(item, "key", "")),
                    "label": _normalize_copy_text(getattr(item, "label", "")),
                }
            )
    return categories


def _empty_catalog_page_payload(requested_lang):
    return {
        "type": "catalogs_cms.CatalogIndexPage",
        "title": "",
        "locale": requested_lang,
        "meta": {
            "seo_title": "",
            "search_description": "",
        },
        "fields": {
            "copy": {
                "catalogs_eyebrow": "",
                "catalogs_heading": "",
                "catalogs_prev_aria": "",
                "catalogs_next_aria": "",
                "catalogs_dot_aria": "",
                "filter_heading": "",
                "filter_all_label": "",
                "empty_state_text": "",
            },
            "categories": [],
            "catalogs": [],
        },
    }


def serialize_catalog_index_page(page, request, requested_lang=None):
    requested_lang = requested_lang or _resolve_language(request)
    response_locale = _normalize_locale_code(
        getattr(getattr(page, "locale", None), "language_code", requested_lang)
    )

    catalogs = []
    items = getattr(page, "catalog_items", None)
    if items is not None and hasattr(items, "all"):
        for item in items.all().order_by("sort_order", "pk"):
            catalogs.append(
                {
                    "title": _normalize_copy_text(getattr(item, "title", "")),
                    "image": _get_image_payload(getattr(item, "image", None), request),
                    "file_url": _get_catalog_download_url(item, request),
                    "categories": _normalize_category_keys(getattr(item, "categories", [])),
                }
            )

    seo_title = _normalize_copy_text(getattr(page, "seo_title", "")) or _normalize_copy_text(
        getattr(page, "title", "")
    )
    search_description = _normalize_copy_text(getattr(page, "search_description", ""))
    meta = {
        "seo_title": seo_title,
        "search_description": search_description,
    }
    translations = build_translations_map(page)
    if translations:
        meta["translations"] = translations

    return {
        "type": "catalogs_cms.CatalogIndexPage",
        "title": _normalize_copy_text(getattr(page, "title", "")),
        "locale": response_locale,
        "meta": meta,
        "fields": {
            "copy": _get_copy(page),
            "categories": _get_categories_payload(page),
            "catalogs": catalogs,
        },
    }


def catalogs_index_api(request):
    requested_lang = _resolve_language(request)
    page = _get_page_for_api(request)

    if page is None:
        return JsonResponse(_empty_catalog_page_payload(requested_lang))

    return JsonResponse(serialize_catalog_index_page(page, request, requested_lang))
