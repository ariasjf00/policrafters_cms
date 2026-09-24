from django.http import JsonResponse

from collections_page.models import CollectionIndexPage, CollectionProductItem
from wagtail.models import Site


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
        return {
            "url": "",
            "alt": _normalize_copy_text(alt_text),
        }

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

    normalized_alt = _normalize_copy_text(alt_text) or _normalize_copy_text(fallback_alt)

    return {
        "url": image_url,
        "alt": normalized_alt,
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


def _get_page_for_api(request):
    lang = _resolve_language(request)
    root_page = _get_site_root_page(request)

    candidate_qs = CollectionIndexPage.objects.select_related("locale").prefetch_related(
        "category_items",
        "type_items",
        "product_items",
    )
    global_qs = CollectionIndexPage.objects.select_related("locale").prefetch_related(
        "category_items",
        "type_items",
        "product_items",
    )

    if root_page is not None:
        candidate_qs = candidate_qs.child_of(root_page)

    locale_candidates = candidate_qs.filter(locale__language_code=lang)
    if not locale_candidates.exists():
        locale_candidates = global_qs.filter(locale__language_code=lang)

    if not locale_candidates.exists() and lang != "en":
        locale_candidates = candidate_qs.filter(locale__language_code="en")

    if not locale_candidates.exists():
        locale_candidates = global_qs.filter(locale__language_code="en")

    if not locale_candidates.exists():
        locale_candidates = candidate_qs

    page = locale_candidates.order_by("-pk").first()
    if page is None:
        page = candidate_qs.order_by("-pk").first()

    return page


def _normalize_product_slug_fragment(slug, category=None, type_key=None):
    candidate = _normalize_copy_text(slug)
    if not candidate:
        return ""

    for prefix in [category, type_key]:
        if not prefix:
            continue
        normalized_prefix = _normalize_copy_text(prefix)
        if candidate == normalized_prefix:
            return ""
        if candidate.startswith(f"{normalized_prefix}/"):
            candidate = candidate[len(normalized_prefix) + 1 :]

    return candidate


def _get_full_product_slug(product):
    category = _normalize_copy_text(getattr(product, "category_key", ""))
    type_key = _normalize_copy_text(getattr(product, "type_key", ""))
    slug = _normalize_product_slug_fragment(getattr(product, "slug", ""), category, type_key)

    parts = []
    if category:
        parts.append(category)
    if type_key:
        parts.append(type_key)
    if slug:
        parts.append(slug)

    full_slug = "/".join(parts)
    if full_slug:
        return full_slug

    return slug


def _product_matches_slug(product, requested_slug):
    normalized = _normalize_copy_text(requested_slug)
    if not normalized:
        return False

    raw_slug = _normalize_copy_text(getattr(product, "slug", ""))
    full_slug = _get_full_product_slug(product)
    normalized_raw = _normalize_product_slug_fragment(raw_slug, _normalize_copy_text(getattr(product, "category_key", "")), _normalize_copy_text(getattr(product, "type_key", "")))
    return normalized in {raw_slug, full_slug, normalized_raw, normalized_raw.split("/")[-1] if "/" in normalized_raw else normalized_raw}


def _get_categories_payload(page, request):
    categories = list(getattr(page, "category_items", []).all().order_by("sort_order", "pk"))
    types = list(getattr(page, "type_items", []).all().order_by("sort_order", "pk"))
    products = list(getattr(page, "product_items", []).all().order_by("sort_order", "pk"))

    payload = []
    for category in categories:
        category_key = _normalize_copy_text(getattr(category, "key", ""))
        category_types = []
        for type_item in types:
            type_category_key = _normalize_copy_text(getattr(type_item, "category_key", ""))
            if not type_category_key:
                type_category_key = _normalize_copy_text(
                    getattr(getattr(type_item, "category", None), "key", "")
                )

            if type_category_key != category_key:
                continue

            type_key = _normalize_copy_text(getattr(type_item, "key", ""))
            type_products = []
            for product in products:
                product_category_key = _normalize_copy_text(getattr(product, "category_key", ""))
                if not product_category_key:
                    product_category_key = _normalize_copy_text(
                        getattr(getattr(product, "collection_category", None), "key", "")
                    )

                if product_category_key != category_key:
                    continue

                product_type_key = _normalize_copy_text(getattr(product, "type_key", ""))
                if not product_type_key:
                    product_type_key = _normalize_copy_text(
                        getattr(getattr(product, "collection_type", None), "key", "")
                    )

                if product_type_key != type_key:
                    continue

                type_products.append(
                    {
                        "title": _normalize_copy_text(getattr(product, "title", "")),
                        "slug": _get_full_product_slug(product),
                        "image": _get_image_payload(
                            getattr(product, "image", None),
                            request,
                            getattr(product, "image_alt", ""),
                        ),
                    }
                )

            category_types.append(
                {
                    "key": type_key,
                    "label": _normalize_copy_text(getattr(type_item, "label", "")),
                    "products": type_products,
                }
            )

        has_products = any(len(type_item["products"]) > 0 for type_item in category_types)

        payload.append(
            {
                "key": category_key,
                "label": _normalize_copy_text(getattr(category, "label", "")),
                "has_products": has_products,
                "types": category_types,
            }
        )

    return payload


def _serialize_download_links(item, request):
    links = getattr(item, "download_links", []) or []
    serialized = []

    if isinstance(links, dict):
        links = [links]

    for link in links:
        if isinstance(link, str):
            serialized.append({"label": link, "url": _normalize_copy_text(link)})
            continue

        if not isinstance(link, dict):
            continue

        label = _normalize_copy_text(link.get("label") or link.get("title") or "Download")
        url = _normalize_copy_text(link.get("url") or link.get("href") or "")
        if url and not url.startswith(("http://", "https://", "//", "mailto:")):
            url = _build_absolute_url(request, url)
        serialized.append({"label": label, "url": url})

    return serialized


def _serialize_related_products(page, product, request):
    related = []
    products = list(
        page.product_items.filter(
            category_key=product.category_key,
        )
        .exclude(pk=product.pk)
        .order_by("sort_order", "pk")[:4]
    )

    if not products and product.category_key:
        products = list(
            page.product_items.filter(type_key=product.type_key)
            .exclude(pk=product.pk)
            .order_by("sort_order", "pk")[:4]
        )

    for related_product in products:
        related.append(
            {
                "title": _normalize_copy_text(getattr(related_product, "title", "")),
                "slug": _get_full_product_slug(related_product),
                "thumbnail": _get_image_payload(
                    getattr(related_product, "image", None),
                    request,
                    getattr(related_product, "image_alt", ""),
                ),
            }
        )

    return related


def serialize_collection_product(page, product, request):
    product_slug = _get_full_product_slug(product)
    category_slug = _normalize_copy_text(getattr(product, "category_key", "")) or ""
    response_locale = _normalize_locale_code(
        getattr(getattr(page, "locale", None), "language_code", "en")
    )

    gallery_pair = []
    for image_field, alt_field in (
        ("gallery_image_1", "gallery_image_1_alt"),
        ("gallery_image_2", "gallery_image_2_alt"),
    ):
        image = getattr(product, image_field, None)
        if image is None:
            continue
        gallery_pair.append(
            _get_image_payload(image, request, getattr(product, alt_field, ""))
        )

    fields = {
        "hero_image": _get_image_payload(getattr(product, "image", None), request, getattr(product, "image_alt", "")),
        "short_description": _normalize_copy_text(getattr(product, "intro_text_1", "")),
        "specs": [],
        "gallery": [],
        "pdf_datasheet": None,
        "brand": {"name": "", "slug": "", "logo": {"url": "", "alt": ""}},
        "collection": {
            "name": _normalize_copy_text(
                next(
                    (
                        category.label
                        for category in getattr(page, "category_items", []).all()
                        if _normalize_copy_text(getattr(category, "key", "")) == category_slug
                    ),
                    category_slug,
                )
            ) or category_slug,
            "slug": category_slug,
        },
        "related_models": _serialize_related_products(page, product, request),
        "intro_text_1": _normalize_copy_text(getattr(product, "intro_text_1", "")),
        "secondary_image": _get_image_payload(
            getattr(product, "secondary_image", None),
            request,
            getattr(product, "image_alt", ""),
        ),
        "intro_text_2": _normalize_copy_text(getattr(product, "intro_text_2", "")),
        "intro_text_product": _normalize_copy_text(
            getattr(product, "intro_text_product", "")
        ),
        "gallery_pair": gallery_pair,
        "product_eyebrow": _normalize_copy_text(getattr(product, "product_eyebrow", "")),
        "product_heading": _normalize_copy_text(getattr(product, "product_heading", "") or getattr(product, "title", "")),
        "product_body": _normalize_copy_text(
            getattr(product, "intro_text_product", "")
            or getattr(product, "intro_text_1", "")
            or getattr(product, "intro_text_2", "")
        ),
        "technical_eyebrow": _normalize_copy_text(getattr(product, "technical_eyebrow", "")),
        "technical_image_product": _get_image_payload(
            getattr(product, "technical_image_product", None),
            request,
            getattr(product, "image_alt", ""),
        ),
        "technical_image_dimensions": _get_image_payload(
            getattr(product, "technical_image_dimensions", None),
            request,
            "",
        ),
        "download_heading": _normalize_copy_text(getattr(product, "download_heading", "")),
        "download_links": _serialize_download_links(product, request),
        "back_to_menu_label": _normalize_copy_text(getattr(product, "back_to_menu_label", "")),
        "breadcrumbs": [],
    }

    if not fields["gallery_pair"]:
        hero_image = fields["hero_image"]
        if hero_image and hero_image.get("url"):
            fields["gallery_pair"] = [hero_image]

    seo_title = _normalize_copy_text(getattr(page, "seo_title", "")) or _normalize_copy_text(
        getattr(page, "title", "")
    )

    return {
        "type": "collections.ModelPage",
        "title": _normalize_copy_text(getattr(product, "title", "")),
        "slug": product_slug,
        "locale": response_locale,
        "meta": {
            "seo_title": seo_title,
            "search_description": _normalize_copy_text(getattr(page, "search_description", "")),
        },
        "fields": fields,
    }


def serialize_collection_index_page(page, request, requested_lang=None):
    requested_lang = requested_lang or _resolve_language(request)
    response_locale = _normalize_locale_code(
        getattr(
            getattr(page, "locale", None),
            "language_code",
            requested_lang,
        )
    )

    seo_title = _normalize_copy_text(getattr(page, "seo_title", "")) or _normalize_copy_text(
        getattr(page, "title", "")
    )

    return {
        "type": "collections.CollectionIndexPage",
        "title": page.title,
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


def _get_product_for_api(request):
    requested_lang = _resolve_language(request)
    page = _get_page_for_api(request)
    if page is None:
        return None, requested_lang

    slug = _normalize_copy_text(request.GET.get("slug") or request.GET.get("product") or "")
    queryset = page.product_items.select_related(
        "image",
        "secondary_image",
        "technical_image_product",
        "technical_image_dimensions",
    )

    product = None
    if slug:
        fallback_qs = queryset.filter(locale__language_code=requested_lang)
        for candidate in fallback_qs.order_by("sort_order", "pk"):
            if _product_matches_slug(candidate, slug):
                product = candidate
                break

    if product is None and requested_lang != "en":
        for candidate in queryset.filter(locale__language_code="en").order_by("sort_order", "pk"):
            if _product_matches_slug(candidate, slug):
                product = candidate
                break

    if product is None and slug:
        for candidate in queryset.order_by("sort_order", "pk"):
            if _product_matches_slug(candidate, slug):
                product = candidate
                break

    if product is None and slug:
        for candidate in queryset.order_by("sort_order", "pk"):
            if _normalize_copy_text(candidate.slug).endswith(slug):
                product = candidate
                break

    return product, requested_lang


def product_detail_api(request):
    requested_lang = _resolve_language(request)
    product, requested_lang = _get_product_for_api(request)
    page = _get_page_for_api(request)

    if product is None or page is None:
        slug = _normalize_copy_text(request.GET.get("slug") or request.GET.get("product") or "")
        return JsonResponse(
            {
                "type": "collections.ModelPage",
                "title": "",
                "slug": slug,
                "locale": requested_lang,
                "meta": {
                    "seo_title": "",
                    "search_description": "",
                },
                "fields": {
                    "hero_image": {"url": "", "alt": ""},
                    "short_description": "",
                    "specs": [],
                    "gallery": [],
                    "pdf_datasheet": None,
                    "brand": {"name": "", "slug": "", "logo": {"url": "", "alt": ""}},
                    "collection": {"name": "", "slug": ""},
                    "related_models": [],
                    "intro_text_1": "",
                    "secondary_image": {"url": "", "alt": ""},
                    "intro_text_2": "",
                    "intro_text_product": "",
                    "gallery_pair": [],
                    "product_eyebrow": "",
                    "product_heading": "",
                    "product_body": "",
                    "technical_eyebrow": "",
                    "technical_image_product": {"url": "", "alt": ""},
                    "technical_image_dimensions": {"url": "", "alt": ""},
                    "download_heading": "",
                    "download_links": [],
                    "back_to_menu_label": "",
                    "breadcrumbs": [],
                },
            }
        )

    data = serialize_collection_product(page, product, request)
    data["locale"] = _normalize_locale_code(
        getattr(getattr(product, "locale", None), "language_code", requested_lang)
    )
    return JsonResponse(data)


def collections_index_api(request):
    requested_lang = _resolve_language(request)
    page = _get_page_for_api(request)

    if page is None:
        return JsonResponse(
            {
                "type": "collections.CollectionIndexPage",
                "title": "",
                "locale": requested_lang,
                "meta": {
                    "seo_title": "",
                    "search_description": "",
                },
                "fields": {
                    "hero_title": "",
                    "intro_text": "",
                    "empty_state_text": "",
                    "categories": [],
                },
            }
        )

    data = serialize_collection_index_page(
        page,
        request,
        requested_lang,
    )
    return JsonResponse(data)
