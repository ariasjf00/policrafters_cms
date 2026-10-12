from django.http import JsonResponse
from wagtail.models import Site

from why_policrafters.models import WhyPolicraftersPage


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


def _normalize_body(value):
    if isinstance(value, list):
        body = []
        for entry in value:
            text = _normalize_copy_text(entry)
            if text:
                body.append(text)
        return body

    text = _normalize_copy_text(value)
    if not text:
        return []
    return [text]


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


def _get_page_for_api(request):
    lang = _resolve_language(request)
    root_page = _get_site_root_page(request)

    candidate_qs = WhyPolicraftersPage.objects.select_related(
        "locale",
        "hero_image",
        "certifications_image",
    ).prefetch_related(
        "why_items",
        "identity_items",
        "partners",
        "partners__logo",
        "partners__image",
        "issuers",
        "issuers__logo",
        "issuers__licenses",
    )
    global_qs = WhyPolicraftersPage.objects.select_related(
        "locale",
        "hero_image",
        "certifications_image",
    ).prefetch_related(
        "why_items",
        "identity_items",
        "partners",
        "partners__logo",
        "partners__image",
        "issuers",
        "issuers__logo",
        "issuers__licenses",
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


def _serialize_text_block_items(items_queryset):
    entries = []
    for item in items_queryset.all().order_by("sort_order", "pk"):
        entries.append(
            {
                "key": _normalize_copy_text(getattr(item, "key", "")),
                "heading": _normalize_copy_text(getattr(item, "heading", "")),
                "body": _normalize_body(getattr(item, "body", [])),
            }
        )
    return entries


def _serialize_issuers(page, request):
    issuers = []
    issuers_queryset = getattr(page, "issuers", None)
    if issuers_queryset is None or not hasattr(issuers_queryset, "all"):
        return issuers

    for issuer in issuers_queryset.all().order_by("sort_order", "pk"):
        licenses = []
        for license_item in issuer.licenses.all().order_by("sort_order", "pk"):
            licenses.append(
                {
                    "label": _normalize_copy_text(getattr(license_item, "label", "")),
                    "number": _normalize_copy_text(getattr(license_item, "number", "")),
                    "caption": _normalize_copy_text(getattr(license_item, "caption", "")),
                }
            )

        issuers.append(
            {
                "key": _normalize_copy_text(getattr(issuer, "key", "")),
                "logo": _get_image_payload(
                    getattr(issuer, "logo", None),
                    request,
                    getattr(issuer, "logo_alt", ""),
                ),
                "licenses": licenses,
            }
        )
    return issuers


def _serialize_partners(page, request):
    partners = []
    partners_queryset = getattr(page, "partners", None)
    if partners_queryset is None or not hasattr(partners_queryset, "all"):
        return partners

    for partner in partners_queryset.all().order_by("sort_order", "pk"):
        partners.append(
            {
                "key": _normalize_copy_text(getattr(partner, "key", "")),
                "logo": _get_image_payload(
                    getattr(partner, "logo", None),
                    request,
                    getattr(partner, "logo_alt", ""),
                ),
                "image": _get_image_payload(
                    getattr(partner, "image", None),
                    request,
                    getattr(partner, "image_alt", ""),
                ),
                "body": _normalize_body(getattr(partner, "body", [])),
            }
        )
    return partners


def _empty_why_page_payload(requested_lang):
    return {
        "type": "why_policrafters.WhyPolicraftersPage",
        "title": "",
        "locale": requested_lang,
        "meta": {
            "seo_title": "",
            "search_description": "",
        },
        "fields": {
            "hero_image": {"url": "", "alt": ""},
            "intro_eyebrow": "",
            "intro_heading": "",
            "intro_body": [],
            "why_eyebrow": "",
            "why_heading": "",
            "why_items": [],
            "certifications_image": {"url": "", "alt": ""},
            "certifications_eyebrow": "",
            "certifications_heading": "",
            "certifications_body": [],
            "issuers": [],
            "identity_eyebrow": "",
            "identity_heading": "",
            "identity_items": [],
            "partners_eyebrow": "",
            "partners_heading": "",
            "partners_intro": "",
            "partners": [],
        },
    }


def serialize_why_policrafters_page(page, request, requested_lang=None):
    requested_lang = requested_lang or _resolve_language(request)
    response_locale = _normalize_locale_code(
        getattr(getattr(page, "locale", None), "language_code", requested_lang)
    )

    seo_title = _normalize_copy_text(getattr(page, "seo_title", "")) or _normalize_copy_text(
        getattr(page, "title", "")
    )

    why_items_queryset = getattr(page, "why_items", None)
    why_items = []
    if why_items_queryset is not None and hasattr(why_items_queryset, "all"):
        why_items = _serialize_text_block_items(why_items_queryset)

    identity_items_queryset = getattr(page, "identity_items", None)
    identity_items = []
    if identity_items_queryset is not None and hasattr(identity_items_queryset, "all"):
        identity_items = _serialize_text_block_items(identity_items_queryset)

    return {
        "type": "why_policrafters.WhyPolicraftersPage",
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
            "intro_body": _normalize_body(getattr(page, "intro_body", [])),
            "why_eyebrow": _normalize_copy_text(getattr(page, "why_eyebrow", "")),
            "why_heading": _normalize_copy_text(getattr(page, "why_heading", "")),
            "why_items": why_items,
            "certifications_image": _get_image_payload(
                getattr(page, "certifications_image", None),
                request,
                getattr(page, "certifications_image_alt", ""),
            ),
            "certifications_eyebrow": _normalize_copy_text(
                getattr(page, "certifications_eyebrow", "")
            ),
            "certifications_heading": _normalize_copy_text(
                getattr(page, "certifications_heading", "")
            ),
            "certifications_body": _normalize_body(getattr(page, "certifications_body", [])),
            "issuers": _serialize_issuers(page, request),
            "identity_eyebrow": _normalize_copy_text(getattr(page, "identity_eyebrow", "")),
            "identity_heading": _normalize_copy_text(getattr(page, "identity_heading", "")),
            "identity_items": identity_items,
            "partners_eyebrow": _normalize_copy_text(getattr(page, "partners_eyebrow", "")),
            "partners_heading": _normalize_copy_text(getattr(page, "partners_heading", "")),
            "partners_intro": _normalize_copy_text(getattr(page, "partners_intro", "")),
            "partners": _serialize_partners(page, request),
        },
    }


def why_policrafters_page_api(request):
    requested_lang = _resolve_language(request)
    page = _get_page_for_api(request)

    if page is None:
        return JsonResponse(_empty_why_page_payload(requested_lang))

    return JsonResponse(serialize_why_policrafters_page(page, request, requested_lang))
