from django.http import JsonResponse

from contact_cms.models import ContactPage
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

    candidate_qs = ContactPage.objects.select_related("locale").prefetch_related("location_items")
    global_qs = ContactPage.objects.select_related("locale").prefetch_related("location_items")

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


def _get_copy(page):
    return {
        "heading": _normalize_copy_text(getattr(page, "heading", "")),
        "intro": _normalize_copy_text(getattr(page, "intro", "")),
        "phone_label": _normalize_copy_text(getattr(page, "phone_label", "")),
        "email_label": _normalize_copy_text(getattr(page, "email_label", "")),
        "project_button_label": _normalize_copy_text(getattr(page, "project_button_label", "")),
        "locations_heading": _normalize_copy_text(getattr(page, "locations_heading", "")),
        "locations_aria": _normalize_copy_text(getattr(page, "locations_aria", "")),
        "learn_more": _normalize_copy_text(getattr(page, "learn_more", "")),
    }


def contact_page_api(request):
    requested_lang = _resolve_language(request)
    page = _get_page_for_api(request)

    if page is None:
        return JsonResponse(
            {
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
                    "locations": [],
                },
            }
        )

    response_locale = _normalize_locale_code(getattr(getattr(page, "locale", None), "language_code", requested_lang))

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

    seo_title = _normalize_copy_text(getattr(page, "seo_title", "")) or _normalize_copy_text(getattr(page, "title", ""))
    search_description = _normalize_copy_text(getattr(page, "search_description", "")) or _normalize_copy_text(getattr(page, "intro", ""))

    data = {
        "type": "contact_cms.ContactPage",
        "title": page.title,
        "locale": response_locale,
        "meta": {
            "seo_title": seo_title,
            "search_description": search_description,
        },
        "fields": {
            "copy": _get_copy(page),
            "contact": {
                "phone_display": _normalize_copy_text(getattr(page, "phone_display", "")),
                "phone_href": _normalize_copy_text(getattr(page, "phone_href", "")) or None,
                "email": _normalize_copy_text(getattr(page, "email", "")),
                "url_contact": _normalize_copy_text(getattr(page, "url_contact", "")),
            },
            "locations": locations,
        },
    }
    return JsonResponse(data)
