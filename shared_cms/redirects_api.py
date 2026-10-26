from urllib.parse import urlsplit

from django.http import JsonResponse
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Site


def redirects_api(request):
    site = Site.find_for_request(request)
    redirects = Redirect.get_for_site(site).select_related("redirect_page")

    items = []
    for redirect in redirects.order_by("old_path", "pk"):
        target = redirect.link
        if not target:
            continue

        old_path = Redirect.normalise_path(redirect.old_path)
        parsed_target = urlsplit(target)
        if redirect.redirect_page_id:
            new_path = parsed_target.path.rstrip("/") or "/"
        elif parsed_target.scheme and parsed_target.netloc:
            new_path = target
        else:
            new_path = parsed_target.path or "/"
            if parsed_target.query:
                new_path = f"{new_path}?{parsed_target.query}"
            if parsed_target.fragment:
                new_path = f"{new_path}#{parsed_target.fragment}"

        items.append(
            {
                "old_path": old_path,
                "new_path": new_path,
                "is_permanent": redirect.is_permanent,
            }
        )

    return JsonResponse(
        {
            "type": "redirects.RedirectList",
            "title": "Redirects",
            "locale": "en",
            "meta": {},
            "fields": {"items": items},
        }
    )
