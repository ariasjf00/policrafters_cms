from django.conf import settings
from urllib.parse import urlsplit
from wagtail.models import Site


UNUSABLE_PREVIEW_HOSTS = {"testsite", "testserver", "example.com"}
UNUSABLE_PREVIEW_PORTS = {"4321"}


def _is_unusable_preview_host(hostname):
    host = str(hostname or "").strip().lower()
    if not host:
        return True

    if host.startswith(("http://", "https://")):
        parsed = urlsplit(host)
        host = parsed.hostname or ""
        if str(parsed.port) in UNUSABLE_PREVIEW_PORTS and host in {"localhost", "127.0.0.1", "0.0.0.0"}:
            return True
    else:
        if ":" in host and host.rsplit(":", 1)[-1].isdigit():
            port = host.rsplit(":", 1)[-1]
            host_name = host.rsplit(":", 1)[0]
            if port in UNUSABLE_PREVIEW_PORTS and host_name in {"localhost", "127.0.0.1", "0.0.0.0"}:
                return True
            host = host_name

    return host in UNUSABLE_PREVIEW_HOSTS


def _site_base_url_from_hostname(hostname, is_secure=None):
    host = str(hostname or "").strip()
    if not host or _is_unusable_preview_host(host):
        return ""

    if host.startswith(("http://", "https://")):
        return host.rstrip("/")

    if is_secure is None:
        is_secure = True
    scheme = "https" if is_secure else "http"
    return f"{scheme}://{host}".rstrip("/")


def normalize_supported_language(value):
    normalized = str(value or "").strip().lower()
    if normalized.startswith("es"):
        return "es"
    if normalized.startswith("en"):
        return "en"
    return None


def resolve_request_language(request, default_lang="en"):
    locale = normalize_supported_language(request.GET.get("locale"))
    if locale:
        return locale

    lang = normalize_supported_language(request.GET.get("lang"))
    if lang:
        return lang

    return default_lang


def build_translations_map(instance, slug_getter=None):
    translation_key = getattr(instance, "translation_key", None)
    if not translation_key:
        return {}

    queryset = (
        instance.__class__.objects.filter(translation_key=translation_key).select_related("locale")
    )
    translations = {}

    for candidate in queryset:
        locale_code = normalize_supported_language(
            getattr(getattr(candidate, "locale", None), "language_code", None)
        )
        if not locale_code:
            continue

        if slug_getter is None:
            slug = getattr(candidate, "slug", "")
        else:
            slug = slug_getter(candidate)

        normalized_slug = str(slug or "").strip()
        if normalized_slug:
            translations[locale_code] = normalized_slug

    return translations


def _request_base_url(request):
    if request is None:
        return ""

    try:
        host = request.get_host()
    except Exception:
        host = request.META.get("HTTP_HOST") or request.META.get("SERVER_NAME") or ""

    host = str(host or "").strip()
    if not host or _is_unusable_preview_host(host):
        return ""

    scheme = "https" if getattr(request, "is_secure", lambda: False)() else "http"
    return f"{scheme}://{host}".rstrip("/")


def build_absolute_asset_url(request, value):
    normalized = str(value or "").strip()
    if not normalized:
        return ""

    if normalized.startswith(("http://", "https://")):
        return normalized

    if normalized.startswith("//"):
        if request is not None and hasattr(request, "is_secure"):
            scheme = "https" if request.is_secure() else "http"
        else:
            scheme = "https"
        return f"{scheme}:{normalized}"

    if normalized.startswith("/"):
        base_url = str(getattr(settings, "WAGTAILADMIN_BASE_URL", "") or "").strip().rstrip("/")
        if base_url and not _is_unusable_preview_host(base_url):
            return f"{base_url}{normalized}"

        request_base_url = _request_base_url(request)
        if request_base_url:
            return f"{request_base_url}{normalized}"

        default_site = Site.objects.filter(is_default_site=True).order_by("-id").first()
        if default_site is not None:
            site_base_url = _site_base_url_from_hostname(
                default_site.hostname,
                is_secure=(request.is_secure() if request is not None else None),
            )
            if site_base_url:
                return f"{site_base_url}{normalized}"

    if request is None:
        return normalized

    try:
        absolute_url = request.build_absolute_uri(normalized)
        if _is_unusable_preview_host(absolute_url):
            return normalized
        return absolute_url
    except Exception:
        return normalized


def get_site_root_page(request):
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


def get_locale_candidates_with_global_fallback(base_queryset, request, lang, default_lang="en"):
    candidate_qs = base_queryset
    root_page = get_site_root_page(request)
    if root_page is not None:
        candidate_qs = candidate_qs.child_of(root_page)

    locale_candidates = candidate_qs.filter(locale__language_code=lang)
    if not locale_candidates.exists():
        locale_candidates = base_queryset.filter(locale__language_code=lang)

    if not locale_candidates.exists() and lang != default_lang:
        locale_candidates = candidate_qs.filter(locale__language_code=default_lang)

    if not locale_candidates.exists():
        locale_candidates = base_queryset.filter(locale__language_code=default_lang)

    if not locale_candidates.exists():
        locale_candidates = candidate_qs

    return locale_candidates, candidate_qs


def get_page_with_locale_fallback(base_queryset, request, lang, default_lang="en"):
    locale_candidates, candidate_qs = get_locale_candidates_with_global_fallback(
        base_queryset,
        request,
        lang,
        default_lang,
    )

    page = locale_candidates.order_by("-pk").first()
    if page is None:
        page = candidate_qs.order_by("-pk").first()
    return page
