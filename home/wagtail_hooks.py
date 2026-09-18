from wagtail.admin.views.pages.edit import EditView
from wagtail.admin.wagtail_hooks import PageListingViewLiveButton

from policrafters_cms.middleware import add_locale_to_url


_original_page_listing_view_live_button_init = PageListingViewLiveButton.__init__
_original_edit_view_get_preview_url = EditView.get_preview_url


def _patched_page_listing_view_live_button_init(self, *args, **kwargs):
    _original_page_listing_view_live_button_init(self, *args, **kwargs)

    page = getattr(self, "page", None)
    locale = getattr(getattr(page, "locale", None), "language_code", None)
    if page and locale and getattr(self, "url", None):
        self.url = add_locale_to_url(self.url, locale)


def _patched_edit_view_get_preview_url(self):
    preview_url = _original_edit_view_get_preview_url(self)
    locale = getattr(getattr(getattr(self, "page", None), "locale", None), "language_code", None)
    if locale:
        preview_url = add_locale_to_url(preview_url, locale)
    return preview_url


PageListingViewLiveButton.__init__ = _patched_page_listing_view_live_button_init
EditView.get_preview_url = _patched_edit_view_get_preview_url