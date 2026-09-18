import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.utils import translation

from wagtail.models import Page


def _normalize_language_code(value):
    if not value:
        return None

    value = value.strip().lower()
    if value.startswith("es"):
        return "es"
    if value.startswith("en"):
        return "en"
    if value in {"en", "es"}:
        return value
    return None


def add_locale_to_url(url, locale_code):
    if not url or not locale_code:
        return url

    locale_code = _normalize_language_code(locale_code) or locale_code.strip().lower()
    split_url = urlsplit(url)
    query_items = [(key, value) for key, value in parse_qsl(split_url.query, keep_blank_values=True) if key not in {"lang", "locale"}]
    query_items.append(("lang", locale_code))
    return urlunsplit(
        (
            split_url.scheme,
            split_url.netloc,
            split_url.path,
            urlencode(query_items, doseq=True),
            split_url.fragment,
        )
    )


def _get_page_locale_from_preview_request(request):
    match = re.search(r"/admin/pages/(\d+)", request.path)
    if not match:
        return None

    try:
        page = Page.objects.select_related("locale").get(id=match.group(1))
    except Page.DoesNotExist:
        return None

    locale = getattr(page, "locale", None)
    if locale and getattr(locale, "language_code", None):
        return locale.language_code

    return None


def force_preview_locale(request):
    """Force locale for CMS preview requests so browser language does not override the page being reviewed."""
    lang = _normalize_language_code(
        request.GET.get("lang") or request.GET.get("locale") or ""
    )

    if not lang:
        lang = _get_page_locale_from_preview_request(request)

    if not lang:
        lang = getattr(request, "LANGUAGE_CODE", "") or "en"
    lang = _normalize_language_code(lang) or "en"

    request.LANGUAGE_CODE = lang
    translation.activate(lang)
    return None


def force_preview_locale_middleware(get_response):
    def middleware(request):
        if (
            request.GET.get("lang")
            or request.GET.get("locale")
            or request.path.startswith("/admin/")
            or request.path.startswith("/cms/")
            or request.path.startswith("/preview/")
        ):
            force_preview_locale(request)
        return get_response(request)

    return middleware
