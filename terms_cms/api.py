from django.http import JsonResponse
from wagtail.models import Site

from terms_cms.models import TermsPage


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


def _get_terms_page_for_api(request):
    lang = _resolve_language(request)
    root_page = _get_site_root_page(request)

    candidate_qs = TermsPage.objects.select_related("locale").prefetch_related("term_items")
    global_qs = TermsPage.objects.select_related("locale").prefetch_related("term_items")

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


def _empty_terms_page_payload(requested_lang):
    return {
        "type": "terms.TermsPage",
        "title": "",
        "locale": requested_lang,
        "meta": {
            "seo_title": "",
            "search_description": "",
        },
        "fields": {
            "intro_heading": "",
            "intro_body": "",
            "terms": [],
        },
    }


def serialize_terms_page(page, request, requested_lang=None):
    requested_lang = requested_lang or _resolve_language(request)
    response_locale = _normalize_locale_code(
        getattr(getattr(page, "locale", None), "language_code", requested_lang)
    )

    terms = []
    items = getattr(page, "term_items", None)
    if items is not None and hasattr(items, "all"):
        for item in items.all().order_by("sort_order", "pk"):
            terms.append(
                {
                    "key": _normalize_copy_text(getattr(item, "key", "")),
                    "title": _normalize_copy_text(getattr(item, "title", "")),
                    "body": _normalize_copy_text(getattr(item, "body", "")),
                }
            )

    seo_title = _normalize_copy_text(getattr(page, "seo_title", "")) or _normalize_copy_text(
        getattr(page, "title", "")
    )
    search_description = _normalize_copy_text(
        getattr(page, "search_description", "")
    ) or _normalize_copy_text(getattr(page, "intro_body", ""))

    return {
        "type": "terms.TermsPage",
        "title": _normalize_copy_text(getattr(page, "title", "")),
        "locale": response_locale,
        "meta": {
            "seo_title": seo_title,
            "search_description": search_description,
        },
        "fields": {
            "intro_heading": _normalize_copy_text(getattr(page, "intro_heading", "")),
            "intro_body": _normalize_copy_text(getattr(page, "intro_body", "")),
            "terms": terms,
        },
    }


def terms_page_api(request):
    requested_lang = _resolve_language(request)
    page = _get_terms_page_for_api(request)

    if page is None:
        return JsonResponse(_empty_terms_page_payload(requested_lang))

    return JsonResponse(serialize_terms_page(page, request, requested_lang))
