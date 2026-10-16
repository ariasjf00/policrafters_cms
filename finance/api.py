from django.http import JsonResponse
from wagtail.models import Site

from finance.models import FinancePage, FinanceStep


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


def _get_finance_page_for_api(request):
    lang = _resolve_language(request)
    root_page = _get_site_root_page(request)

    candidate_qs = FinancePage.objects.select_related("locale", "hero_image").prefetch_related("steps")
    global_qs = FinancePage.objects.select_related("locale", "hero_image").prefetch_related("steps")

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


def _empty_finance_page_payload(requested_lang):
    return {
        "type": "finance.FinancePage",
        "title": "",
        "locale": requested_lang,
        "meta": {
            "seo_title": "",
            "search_description": "",
        },
        "fields": {
            "hero_image": {"url": "", "alt": ""},
            "intro_heading": "",
            "intro_body": "",
            "steps": [],
            "contact": {
                "heading": "",
                "phone_display": "",
                "phone_href": "",
                "email_label": "",
                "email": "",
            },
        },
    }


def serialize_finance_page(page, request, requested_lang=None):
    requested_lang = requested_lang or _resolve_language(request)
    response_locale = _normalize_locale_code(
        getattr(getattr(page, "locale", None), "language_code", requested_lang)
    )

    steps = []
    step_qs = getattr(page, "steps", None)
    if step_qs is not None and hasattr(step_qs, "all"):
        ordered_steps = sorted(
            step_qs.all(),
            key=lambda step: (
                getattr(step, "sort_order", None) if getattr(step, "sort_order", None) is not None else 10**9,
                getattr(step, "pk", 0),
            ),
        )
        for index, step in enumerate(ordered_steps):
            column = _normalize_copy_text(getattr(step, "column", "")).lower()
            if column not in {"left", "right"}:
                column = "left" if index % 2 == 0 else "right"

            steps.append(
                {
                    "key": _normalize_copy_text(getattr(step, "key", "")),
                    "title": _normalize_copy_text(getattr(step, "title", "")),
                    "subtitle": _normalize_copy_text(getattr(step, "subtitle", "")),
                    "body": _normalize_copy_text(getattr(step, "body", "")),
                    "column": column,
                }
            )

    seo_title = _normalize_copy_text(getattr(page, "seo_title", "")) or _normalize_copy_text(
        getattr(page, "title", "")
    )
    search_description = _normalize_copy_text(
        getattr(page, "search_description", "")
    ) or _normalize_copy_text(getattr(page, "intro_body", ""))

    return {
        "type": "finance.FinancePage",
        "title": _normalize_copy_text(getattr(page, "title", "")),
        "locale": response_locale,
        "meta": {
            "seo_title": seo_title,
            "search_description": search_description,
        },
        "fields": {
            "hero_image": _get_image_payload(
                getattr(page, "hero_image", None),
                request,
                getattr(page, "hero_image_alt", ""),
            ),
            "intro_heading": _normalize_copy_text(getattr(page, "intro_heading", "")),
            "intro_body": _normalize_copy_text(getattr(page, "intro_body", "")),
            "steps": steps,
            "contact": {
                "heading": _normalize_copy_text(getattr(page, "contact_heading", "")),
                "phone_display": _normalize_copy_text(getattr(page, "contact_phone_display", "")),
                "phone_href": _normalize_copy_text(getattr(page, "contact_phone_href", "")),
                "email_label": _normalize_copy_text(getattr(page, "contact_email_label", "")),
                "email": _normalize_copy_text(getattr(page, "contact_email", "")),
            },
        },
    }


def finance_page_api(request):
    requested_lang = _resolve_language(request)
    page = _get_finance_page_for_api(request)

    if page is None:
        return JsonResponse(_empty_finance_page_payload(requested_lang))

    return JsonResponse(serialize_finance_page(page, request, requested_lang))
