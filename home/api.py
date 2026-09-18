from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import re

from home.models import HomePage
from wagtail.models import Site


def _get_related_items_payload(items, mapper):
    if items is None:
        return []

    payload = []
    for item in items:
        payload.append(mapper(item))
    return payload


def _serialize_richtext(value):
    # API should not leak Draftail/editor-only attributes.
    html = str(value or "")
    return re.sub(r"\sdata-block-key=(\"[^\"]*\"|'[^']*')", "", html)


def _resolve_language(request):
    lang = (request.GET.get("lang") or request.GET.get("locale") or "en").strip().lower()

    if lang.startswith("es"):
        return "es"
    if lang.startswith("en"):
        return "en"

    return "en"


def _build_absolute_url(request, value):
    url = _normalize_copy_text(value)
    if not url:
        return ""

    if url.startswith(("http://", "https://")):
        return url

    if url.startswith("//"):
        return f"{request.scheme}:{url}"

    if request is None:
        return url

    try:
        return request.build_absolute_uri(url)
    except Exception:
        return url


def _get_image_payload(image, request=None):
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

    return {"url": image_url, "alt": alt_text}


def _normalize_image_dict(value, request):
    image_data = _get_json_dict(value)
    return {
        "url": _build_absolute_url(request, image_data.get("url")),
        "alt": _normalize_copy_text(image_data.get("alt")),
    }


def _get_json_dict(value):
    return value if isinstance(value, dict) else {}


def _get_json_list(value):
    return value if isinstance(value, list) else []


def _normalize_locale_code(locale_code):
    locale = str(locale_code or "").lower()
    if locale.startswith("es"):
        return "es"
    return "en"


REQUIRED_COPY_KEYS = [
    "hero_eyebrow",
    "hero_heading",
    "hero_cta",
    "projects_eyebrow",
    "projects_heading",
    "projects_cta",
    "projects_prev_aria",
    "projects_next_aria",
    "projects_carousel_aria",
    "projects_dot_aria",
    "about_eyebrow",
    "about_heading",
    "about_body_1",
    "about_body_2",
    "about_brands_label",
    "about_cta",
    "team_eyebrow",
    "team_heading",
    "values_eyebrow",
    "values_heading",
    "values_prev_aria",
    "values_next_aria",
    "values_carousel_aria",
    "values_dot_aria",
    "contact_heading",
    "contact_cta",
]

DEFAULT_COPY_TEXT = {
    "hero_eyebrow": {"es": "Inicio", "en": "Home"},
    "hero_heading": {"es": "Bienvenido", "en": "Welcome"},
    "hero_cta": {"es": "Contáctanos", "en": "Contact us"},
    "projects_eyebrow": {"es": "Proyectos", "en": "Projects"},
    "projects_heading": {"es": "Nuestros proyectos", "en": "Our projects"},
    "projects_cta": {"es": "Ver proyectos", "en": "View projects"},
    "projects_prev_aria": {"es": "Proyecto anterior", "en": "Previous project"},
    "projects_next_aria": {"es": "Proyecto siguiente", "en": "Next project"},
    "projects_carousel_aria": {"es": "Carrusel de proyectos", "en": "Projects carousel"},
    "projects_dot_aria": {"es": "Ir al proyecto", "en": "Go to project"},
    "about_eyebrow": {"es": "Nosotros", "en": "About us"},
    "about_heading": {"es": "Sobre nosotros", "en": "About us"},
    "about_body_1": {"es": "Somos una marca dedicada a la creatividad y la excelencia.", "en": "We are a brand dedicated to creativity and excellence."},
    "about_body_2": {"es": "Diseñamos soluciones modernas y funcionales para cada espacio.", "en": "We design modern, functional solutions for every space."},
    "about_brands_label": {"es": "Nuestras marcas", "en": "Our brands"},
    "about_cta": {"es": "Saber más", "en": "Learn more"},
    "team_eyebrow": {"es": "Equipo", "en": "Team"},
    "team_heading": {"es": "Nuestro equipo", "en": "Our team"},
    "values_eyebrow": {"es": "Valores", "en": "Values"},
    "values_heading": {"es": "Nuestros valores", "en": "Our values"},
    "values_prev_aria": {"es": "Valor anterior", "en": "Previous value"},
    "values_next_aria": {"es": "Valor siguiente", "en": "Next value"},
    "values_carousel_aria": {"es": "Carrusel de valores", "en": "Values carousel"},
    "values_dot_aria": {"es": "Ir al valor", "en": "Go to value"},
    "contact_heading": {"es": "Contáctanos", "en": "Contact us"},
    "contact_cta": {"es": "Saber más", "en": "Learn more"},
}


def _normalize_copy_text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def _as_bilingual_text(value, default_value=None):
    default_value = default_value or {"es": "", "en": ""}
    if isinstance(value, dict):
        es = _normalize_copy_text(value.get("es")) or _normalize_copy_text(value.get("es_ES")) or _normalize_copy_text(value.get("es-ES"))
        en = _normalize_copy_text(value.get("en")) or _normalize_copy_text(value.get("en_US")) or _normalize_copy_text(value.get("en-US"))
        if not es and not en:
            es = _normalize_copy_text(default_value.get("es"))
            en = _normalize_copy_text(default_value.get("en"))
        if not es and en:
            es = en
        if not en and es:
            en = es
        if not es and not en:
            es = _normalize_copy_text(default_value.get("es")) or "Text"
            en = _normalize_copy_text(default_value.get("en")) or "Text"
        return {"es": es, "en": en}

    text = _normalize_copy_text(value)
    if not text:
        text = _normalize_copy_text(default_value.get("es")) or _normalize_copy_text(default_value.get("en")) or "Text"
    return {"es": text, "en": text}


def _resolve_localized_value(value, lang, default_value=""):
    if isinstance(value, dict):
        primary = _normalize_copy_text(value.get(lang))
        if not primary:
            primary = _normalize_copy_text(value.get(f"{lang}_{lang.upper()}"))
        if not primary:
            primary = _normalize_copy_text(value.get(f"{lang}-{lang.upper()}"))
        if not primary:
            other_lang = "es" if lang == "en" else "en"
            primary = _normalize_copy_text(value.get(other_lang))
        if not primary:
            primary = _normalize_copy_text(default_value)
        return primary

    text = _normalize_copy_text(value)
    if text:
        return text

    if isinstance(default_value, dict):
        return _resolve_localized_value(default_value, lang, "")

    return _normalize_copy_text(default_value)


def _resolve_localized_entry(item, base_key, lang, default_value=""):
    if not isinstance(item, dict):
        return _resolve_localized_value(None, lang, default_value)

    direct_value = item.get(base_key)
    if isinstance(direct_value, dict):
        resolved = _resolve_localized_value(direct_value, lang, default_value)
        if resolved:
            return resolved

    lang_value = item.get(f"{base_key}_{lang}")
    if _normalize_copy_text(lang_value):
        return _normalize_copy_text(lang_value)

    alt_lang = "es" if lang == "en" else "en"
    alt_value = item.get(f"{base_key}_{alt_lang}")
    if _normalize_copy_text(alt_value):
        return _normalize_copy_text(alt_value)

    return _resolve_localized_value(direct_value, lang, default_value)


def _get_home_copy(page, lang):
    home_copy = _get_json_dict(getattr(page, "home_copy", {}))
    legacy_page_values = {
        "hero_cta": getattr(page, "cta_button_text", None),
        "about_body_1": _serialize_richtext(getattr(page, "intro_text", None)),
        "contact_heading": getattr(page, "cta_heading", None),
        "contact_cta": getattr(page, "cta_button_text", None),
    }

    copy_data = {}
    for key in REQUIRED_COPY_KEYS:
        primary_value = home_copy.get(key)
        if primary_value is None:
            model_value = getattr(page, key, None)
            if model_value not in (None, ""):
                primary_value = model_value
        if primary_value is None and key in legacy_page_values:
            primary_value = legacy_page_values.get(key)
        if primary_value is None:
            primary_value = ""

        fallback_value = DEFAULT_COPY_TEXT.get(key, {"es": "Text", "en": "Text"})
        copy_data[key] = _resolve_localized_value(primary_value, lang, fallback_value)

    return copy_data


def _get_legacy_featured_projects(page, lang, request):
    items = _get_json_list(getattr(page, "featured_projects", []))
    payload = []
    for item in items:
        if not isinstance(item, dict):
            continue
        payload.append({
            "title": _resolve_localized_entry(item, "title", lang, ""),
            "slug": _normalize_copy_text(item.get("slug")),
            "thumbnail": _normalize_image_dict(item.get("thumbnail"), request),
            "description": _resolve_localized_entry(item, "description", lang, ""),
        })
    return payload


def _get_legacy_team_members(page, lang, request):
    items = _get_json_list(getattr(page, "team_members", []))
    payload = []
    for item in items:
        if not isinstance(item, dict):
            continue
        payload.append({
            "name": _normalize_copy_text(item.get("name")),
            "role": _resolve_localized_entry(item, "role", lang, ""),
            "photo": _normalize_image_dict(item.get("photo"), request),
            "bio": _resolve_localized_entry(item, "bio", lang, ""),
        })
    return payload


def _get_legacy_values_slides(page, lang, request):
    items = _get_json_list(getattr(page, "values_slides", []))
    payload = []
    for item in items:
        if not isinstance(item, dict):
            continue
        payload.append({
            "title": _resolve_localized_entry(item, "title", lang, ""),
            "image": _normalize_image_dict(item.get("image"), request),
            "description": _resolve_localized_entry(item, "description", lang, ""),
        })
    return payload


def _get_legacy_contact_links(page, lang):
    items = _get_json_list(getattr(page, "contact_links", []))
    payload = []
    for item in items:
        if not isinstance(item, dict):
            continue
        payload.append({
            "title": _resolve_localized_entry(item, "title", lang, ""),
            "description": _resolve_localized_entry(item, "description", lang, ""),
            "url": _normalize_copy_text(item.get("url")),
        })
    return payload


def _get_site_root_page(request):
    default_site = Site.objects.filter(is_default_site=True).order_by('-id').first()
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


def _home_page_has_content(page):
    if page is None:
        return False

    core_fields = (
        "hero_heading",
        "hero_subheading",
        "cta_heading",
        "cta_button_text",
        "intro_text",
        "home_copy",
    )
    for field_name in core_fields:
        value = getattr(page, field_name, None)
        if value not in (None, "", [], {}, False):
            return True

    if getattr(page, "featured_projects_items", None) is not None and page.featured_projects_items.count() > 0:
        return True
    if getattr(page, "team_members_items", None) is not None and page.team_members_items.count() > 0:
        return True
    if getattr(page, "featured_projects", None):
        return True
    if getattr(page, "team_members", None):
        return True
    return False


def _merge_revision_overrides(page, revision_page):
    if revision_page is None:
        return page

    override_fields = [
        "hero_video_url",
        "hero_video_horizontal",
        "hero_video_vertical",
        "hero_image_fallback",
        "hero_image_horizontal",
        "hero_image_vertical",
        "home_copy",
        "hero_heading",
        "hero_subheading",
        "intro_text",
        "cta_heading",
        "cta_button_text",
        "cta_button_url",
    ]

    live_project_count = page.featured_projects_items.count() if hasattr(page, "featured_projects_items") else 0
    live_team_count = page.team_members_items.count() if hasattr(page, "team_members_items") else 0
    revision_project_count = revision_page.featured_projects_items.count() if hasattr(revision_page, "featured_projects_items") else 0
    revision_team_count = revision_page.team_members_items.count() if hasattr(revision_page, "team_members_items") else 0

    if (live_project_count > 0 or live_team_count > 0) and (revision_project_count == 0 and revision_team_count == 0):
        return page

    for field_name in override_fields:
        if not hasattr(revision_page, field_name):
            continue

        value = getattr(revision_page, field_name)
        if value is not None:
            setattr(page, field_name, value)

    return page


def _home_page_priority(page):
    if page is None:
        return -1

    featured_count = getattr(page, "featured_projects_items", None).count() if getattr(page, "featured_projects_items", None) is not None else 0
    team_count = getattr(page, "team_members_items", None).count() if getattr(page, "team_members_items", None) is not None else 0

    score = 0
    if _home_page_has_content(page):
        score += 1000000
    score += (featured_count * 1000) + (team_count * 1000)
    score += 1 if getattr(page, "live_revision_id", None) else 0
    return score


def _get_page_for_api(request):
    lang = _resolve_language(request)
    root_page = _get_site_root_page(request)

    candidate_qs = HomePage.objects.select_related("locale").prefetch_related("featured_projects_items", "team_members_items")
    global_qs = HomePage.objects.select_related("locale").prefetch_related("featured_projects_items", "team_members_items")
    if root_page is not None:
        candidate_qs = candidate_qs.child_of(root_page)

    locale_candidates = candidate_qs.filter(locale__language_code=lang)
    if not locale_candidates.exists():
        # If the current site tree has no requested locale, try globally.
        locale_candidates = global_qs.filter(locale__language_code=lang)
    if not locale_candidates.exists() and lang != "en":
        locale_candidates = candidate_qs.filter(locale__language_code="en")
    if not locale_candidates.exists():
        locale_candidates = global_qs.filter(locale__language_code="en")
    if not locale_candidates.exists():
        locale_candidates = candidate_qs

    candidates = list(locale_candidates)
    if not candidates:
        candidates = list(candidate_qs)

    if not candidates:
        return get_object_or_404(HomePage, pk=HomePage.objects.order_by("-pk").values_list("pk", flat=True).first())

    page = max(candidates, key=_home_page_priority)

    latest_revision = page.get_latest_revision()
    if latest_revision is not None:
        revision_page = latest_revision.as_object()
        if revision_page is not None:
            live_project_count = page.featured_projects_items.count() if hasattr(page, "featured_projects_items") else 0
            live_team_count = page.team_members_items.count() if hasattr(page, "team_members_items") else 0
            revision_project_count = revision_page.featured_projects_items.count() if hasattr(revision_page, "featured_projects_items") else 0
            revision_team_count = revision_page.team_members_items.count() if hasattr(revision_page, "team_members_items") else 0

            if (live_project_count > 0 or live_team_count > 0) and (revision_project_count == 0 and revision_team_count == 0):
                return page

            if (live_project_count == 0 and live_team_count == 0) and (revision_project_count > 0 or revision_team_count > 0):
                return _merge_revision_overrides(page, revision_page)

            if _home_page_has_content(revision_page):
                return _merge_revision_overrides(page, revision_page)

    return page


def home_page_api(request):
    requested_lang = _resolve_language(request)
    page = _get_page_for_api(request)
    if page is None:
        return JsonResponse({"type": "home_cms.HomePage", "title": "", "locale": "en", "meta": {"seo_title": "", "search_description": ""}, "fields": {"copy": _get_home_copy(HomePage(), "en"), "hero_video_horizontal": None, "hero_video_vertical": None, "hero_image_horizontal": {"url": "", "alt": ""}, "hero_image_vertical": {"url": "", "alt": ""}, "site_logo": {"url": "", "alt": ""}, "featured_projects": [], "team_members": [], "values_slides": [], "contact_links": []}})

    response_locale = _normalize_locale_code(getattr(getattr(page, "locale", None), "language_code", requested_lang))

    hero_video_horizontal = getattr(page, "hero_video_horizontal", None) or getattr(page, "hero_video_url", None) or None
    hero_video_vertical = getattr(page, "hero_video_vertical", None) or getattr(page, "hero_video_url", None) or None
    hero_image_horizontal = getattr(page, "hero_image_horizontal", None) or getattr(page, "hero_image_fallback", None)
    hero_image_vertical = getattr(page, "hero_image_vertical", None) or getattr(page, "hero_image_fallback", None)
    site_logo = getattr(page, "site_logo", None)

    project_items = getattr(page, "featured_projects_items", None)
    if project_items is not None and hasattr(project_items, "all"):
        featured_projects = _get_related_items_payload(project_items.all(), lambda item: {
            "title": item.title or "",
            "slug": item.slug or "",
            "thumbnail": _get_image_payload(getattr(item, "thumbnail", None), request),
            "description": item.description or "",
        })
    else:
        featured_projects = _get_legacy_featured_projects(page, response_locale, request)

    team_items = getattr(page, "team_members_items", None)
    if team_items is not None and hasattr(team_items, "all"):
        team_members = _get_related_items_payload(team_items.all(), lambda item: {
            "name": item.name or "",
            "role": item.role or "",
            "photo": _get_image_payload(getattr(item, "photo", None), request),
            "bio": item.bio or "",
        })
    else:
        team_members = _get_legacy_team_members(page, response_locale, request)

    values_items = getattr(page, "values_slide_items", None)
    if values_items is not None and hasattr(values_items, "all"):
        values_slides = _get_related_items_payload(values_items.all(), lambda item: {
            "title": item.title or "",
            "image": _get_image_payload(getattr(item, "image", None), request),
            "description": item.description or "",
        })
    else:
        values_slides = _get_legacy_values_slides(page, response_locale, request)

    contact_items = getattr(page, "contact_link_items", None)
    if contact_items is not None and hasattr(contact_items, "all"):
        contact_links = _get_related_items_payload(contact_items.all(), lambda item: {
            "title": item.title or "",
            "description": item.description or "",
            "url": item.url or "",
        })
    else:
        contact_links = _get_legacy_contact_links(page, response_locale)

    seo_title = _normalize_copy_text(getattr(page, "seo_title", "")) or _normalize_copy_text(getattr(page, "title", ""))
    search_description = _normalize_copy_text(getattr(page, "search_description", "")) or _normalize_copy_text(_get_home_copy(page, response_locale).get("hero_heading", ""))

    data = {
        "type": "home_cms.HomePage",
        "title": page.title,
        "locale": response_locale,
        "meta": {
            "seo_title": seo_title,
            "search_description": search_description,
        },
        "fields": {
            "copy": _get_home_copy(page, response_locale),
            "hero_video_horizontal": hero_video_horizontal,
            "hero_video_vertical": hero_video_vertical,
            "hero_image_horizontal": _get_image_payload(hero_image_horizontal, request),
            "hero_image_vertical": _get_image_payload(hero_image_vertical, request),
            "site_logo": _get_image_payload(site_logo, request),
            "featured_projects": featured_projects,
            "team_members": team_members,
            "values_slides": values_slides,
            "contact_links": contact_links,
        },
    }

    return JsonResponse(data)
