from django.http import JsonResponse

from renovations.models import RenovationIndexPage
from shared_cms.api_utils import (
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


def _get_renovations_page_for_api(request):
    lang = _resolve_language(request)
    queryset = RenovationIndexPage.objects.select_related("locale").prefetch_related(
        "category_items",
        "type_items",
        "product_items",
    )
    return get_page_with_locale_fallback(queryset, request, lang)


def _get_categories_payload(page, request):
    categories = list(getattr(page, "category_items", []).all().order_by("sort_order", "pk"))
    types = list(getattr(page, "type_items", []).all().order_by("sort_order", "pk"))
    products = list(getattr(page, "product_items", []).all().order_by("sort_order", "pk"))

    payload = []
    for category in categories:
        category_key = _normalize_copy_text(getattr(category, "key", ""))
        category_types = []
        for type_item in types:
            if _normalize_copy_text(getattr(type_item, "category_key", "")) and _normalize_copy_text(getattr(type_item, "category_key", "")) != category_key:
                continue
            if not _normalize_copy_text(getattr(type_item, "category_key", "")) and category_key:
                continue

            type_key = _normalize_copy_text(getattr(type_item, "key", ""))
            type_products = []
            for product in products:
                product_category_key = _normalize_copy_text(getattr(product, "category_key", ""))
                if product_category_key != category_key:
                    continue
                product_type_key = _normalize_copy_text(getattr(product, "type_key", ""))
                if type_key and product_type_key and product_type_key != type_key:
                    continue
                if type_key and not product_type_key:
                    continue

                type_products.append(
                    {
                        "title": _normalize_copy_text(getattr(product, "title", "")),
                        "slug": _normalize_copy_text(getattr(product, "slug", "")),
                        "image": _get_image_payload(
                            getattr(product, "image", None),
                            request,
                            getattr(product, "image_alt", ""),
                        ),
                    }
                )

            if type_key:
                category_types.append(
                    {
                        "key": type_key,
                        "label": _normalize_copy_text(getattr(type_item, "label", "")),
                        "products": type_products,
                    }
                )

        has_products = any(len(type_item["products"]) > 0 for type_item in category_types)

        if not category_types and category_key:
            category_types = [
                {
                    "key": category_key,
                    "label": _normalize_copy_text(getattr(category, "label", "")),
                    "products": [
                        {
                            "title": _normalize_copy_text(getattr(product, "title", "")),
                            "slug": _normalize_copy_text(getattr(product, "slug", "")),
                            "image": _get_image_payload(
                                getattr(product, "image", None),
                                request,
                                getattr(product, "image_alt", ""),
                            ),
                        }
                        for product in products
                        if _normalize_copy_text(getattr(product, "category_key", "")) == category_key
                        and not _normalize_copy_text(getattr(product, "type_key", ""))
                    ],
                }
            ]
            has_products = bool(category_types[0]["products"])

        payload.append(
            {
                "key": category_key,
                "label": _normalize_copy_text(getattr(category, "label", "")),
                "has_products": has_products,
                "show_type_filters": getattr(category, "show_type_filters", True),
                "types": category_types or [
                    {
                        "key": category_key,
                        "label": _normalize_copy_text(getattr(category, "label", "")),
                        "products": [],
                    }
                ],
            }
        )

    return payload


def serialize_renovation_index_page(page, request, requested_lang=None):
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
        "type": "renovations.RenovationIndexPage",
        "title": _normalize_copy_text(getattr(page, "title", "")),
        "locale": response_locale,
        "meta": meta,
        "fields": {
            "hero_title": _normalize_copy_text(getattr(page, "hero_title", "")),
            "intro_text": _normalize_copy_text(getattr(page, "intro_text", "")),
            "empty_state_text": _normalize_copy_text(getattr(page, "empty_state_text", "")),
            "categories": _get_categories_payload(page, request),
        },
    }


def renovation_index_api(request):
    requested_lang = _resolve_language(request)
    page = _get_renovations_page_for_api(request)

    if page is None:
        return JsonResponse(
            {
                "type": "renovations.RenovationIndexPage",
                "title": "",
                "locale": requested_lang,
                "meta": {"seo_title": "", "search_description": ""},
                "fields": {"hero_title": "", "intro_text": "", "empty_state_text": "", "categories": []},
            }
        )

    return JsonResponse(serialize_renovation_index_page(page, request, requested_lang))
