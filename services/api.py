from django.http import JsonResponse
from wagtail.models import Site

from services.models import ServicesPage


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


def _get_services_page_for_api(request):
    lang = _resolve_language(request)
    root_page = _get_site_root_page(request)

    queryset = ServicesPage.objects.select_related("locale", "hero_image").prefetch_related(
        "service_items",
        "service_items__image",
    )
    if root_page is not None:
        queryset = queryset.child_of(root_page)

    page = queryset.filter(locale__language_code=lang).order_by("-pk").first()
    if page is None and lang != "en":
        page = queryset.filter(locale__language_code="en").order_by("-pk").first()
    if page is None:
        page = queryset.order_by("-pk").first()
    return page


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

    return {
        "type": "services.ServicesPage",
        "title": _normalize_copy_text(getattr(page, "title", "")),
        "locale": response_locale,
        "meta": {
            "seo_title": seo_title,
            "search_description": _normalize_copy_text(getattr(page, "search_description", "")),
        },
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
