from django.http import JsonResponse
from wagtail.models import Site

from renovations.models import RenovationIndexPage


def _resolve_language(request):
    lang = (request.GET.get("lang") or request.GET.get("locale") or "en").strip().lower()
    if lang.startswith("es"):
        return "es"
    if lang.startswith("en"):
        return "en"
    return "en"


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
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    if url.startswith("//"):
        return f"{request.scheme}:{url}"
    try:
        return request.build_absolute_uri(url)
    except Exception:
        return url


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


def _get_site_root_page(request):
    default_site = Site.objects.filter(is_default_site=True).order_by("-id").first()
    if default_site is not None and default_site.root_page_id is not None:
        return default_site.root_page.specific

    site = getattr(request, "site", None)
    if site is not None and site.root_page_id is not None:
        return site.root_page.specific

    try:
        site = Site.find_for_request(request)
    except Exception:
        site = None

    if site is not None and site.root_page_id is not None:
        return site.root_page.specific

    return None


def _get_renovations_page_for_api(request):
    lang = _resolve_language(request)
    root_page = _get_site_root_page(request)

    queryset = RenovationIndexPage.objects.select_related("locale").prefetch_related(
        "category_items",
        "type_items",
        "product_items",
    )
    if root_page is not None:
        queryset = queryset.child_of(root_page)

    page = queryset.filter(locale__language_code=lang).order_by("-pk").first()
    if page is None and lang != "en":
        page = queryset.filter(locale__language_code="en").order_by("-pk").first()
    if page is None:
        page = queryset.order_by("-pk").first()
    return page


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

    return {
        "type": "renovations.RenovationIndexPage",
        "title": _normalize_copy_text(getattr(page, "title", "")),
        "locale": response_locale,
        "meta": {
            "seo_title": seo_title,
            "search_description": _normalize_copy_text(getattr(page, "search_description", "")),
        },
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
