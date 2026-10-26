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


def _normalize_image_text(value):
    if value is None or isinstance(value, (dict, list)):
        return ""
    return " ".join(str(value).split())


def normalize_image_payload(value, request):
    image_data = value if isinstance(value, dict) else {}
    payload = {
        "url": build_absolute_asset_url(request, image_data.get("url")),
        "alt": _normalize_image_text(image_data.get("alt")),
    }

    for dimension in ("width", "height"):
        dimension_value = image_data.get(dimension)
        if (
            isinstance(dimension_value, int)
            and not isinstance(dimension_value, bool)
            and dimension_value > 0
        ):
            payload[dimension] = dimension_value

    rendition_data = image_data.get("renditions")
    if isinstance(rendition_data, dict):
        renditions = {}
        for width, url in rendition_data.items():
            width_key = _normalize_image_text(width)
            rendition_url = build_absolute_asset_url(request, url)
            if width_key and rendition_url:
                renditions[width_key] = rendition_url
        if renditions:
            payload["renditions"] = renditions

    return payload


def serialize_image_payload(image, request=None, alt_text=""):
    if image is None:
        return {
            "url": "",
            "alt": _normalize_image_text(alt_text),
        }

    image_file = getattr(image, "file", None)
    image_url = image_file.url if image_file else ""
    payload = {
        "url": build_absolute_asset_url(request, image_url),
        "alt": _normalize_image_text(alt_text),
    }

    if not payload["alt"]:
        for attribute in ("alt", "alt_text", "description", "title"):
            payload["alt"] = _normalize_image_text(getattr(image, attribute, None))
            if payload["alt"]:
                break

    for dimension in ("width", "height"):
        dimension_value = getattr(image, dimension, None)
        if (
            isinstance(dimension_value, int)
            and not isinstance(dimension_value, bool)
            and dimension_value > 0
        ):
            payload[dimension] = dimension_value

    get_renditions = getattr(image, "get_renditions", None)
    is_svg = getattr(image, "is_svg", None)
    if image_file and callable(get_renditions) and not (callable(is_svg) and is_svg()):
        rendition_widths = (800, 1600)
        rendition_specs = tuple(
            f"width-{width}|format-webp" for width in rendition_widths
        )
        generated_renditions = get_renditions(*rendition_specs)
        renditions = {}
        for width, spec in zip(rendition_widths, rendition_specs):
            rendition = generated_renditions.get(spec)
            if rendition is not None and getattr(rendition, "file", None):
                rendition_url = build_absolute_asset_url(
                    request,
                    rendition.file.url,
                )
                if rendition_url:
                    renditions[str(width)] = rendition_url
        if renditions:
            payload["renditions"] = renditions

    return payload


def _public_locale_prefix(locale_code):
    code = normalize_supported_language(locale_code)
    if code == "es":
        return "/es"
    return ""


def build_public_page_url(page, locale_code=None, site_url=None):
    if page is None:
        return ""

    candidate_url = ""
    if hasattr(page, "url"):
        candidate_url = str(getattr(page, "url", "") or "")
    if not candidate_url and hasattr(page, "url_path"):
        candidate_url = str(getattr(page, "url_path", "") or "")
    if not candidate_url and hasattr(page, "live"):
        candidate_url = str(getattr(page.live, "url", "") or "")

    if not candidate_url and isinstance(page, str):
        candidate_url = page

    page_path = str(candidate_url or "").strip()
    if not page_path:
        return ""

    parsed = urlsplit(page_path)
    if parsed.scheme and parsed.netloc:
        page_path = parsed.path or "/"

    page_path = page_path or "/"
    page_path = page_path.rstrip("/") or "/"

    if page.__class__.__name__ == "HomePage" and page_path.lower().endswith("/home"):
        page_path = "/"
    elif page.__class__.__name__ == "HomePage" and page_path.lower().endswith("/home-2"):
        page_path = "/"

    locale_prefix = _public_locale_prefix(locale_code)
    if locale_code is None and hasattr(page, "locale"):
        locale_prefix = _public_locale_prefix(getattr(page.locale, "language_code", None))

    if page_path == "/":
        localized_path = locale_prefix or "/"
    else:
        if locale_prefix and not page_path.startswith(locale_prefix):
            localized_path = f"{locale_prefix}{page_path}"
        else:
            localized_path = page_path

    base_url = str(site_url or getattr(settings, "SITE_URL", "https://policrafters.com") or "https://policrafters.com").strip().rstrip("/")
    return f"{base_url}{localized_path}"


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
