from django.conf import settings
from django.urls import include, path
from django.contrib import admin

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from catalogs_cms.api import catalogs_index_api
from collections_page.api import collections_index_api, product_detail_api
from contact_cms.api import contact_page_api
from home.api import direct_contact_api, home_page_api
from renovations.api import renovation_index_api
from search import views as search_views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("api/home", home_page_api, name="home_page_api"),
    path("api/home/", home_page_api),
    path("api/direct-contact", direct_contact_api, name="direct_contact_api"),
    path("api/direct-contact/", direct_contact_api),
    path("api/catalogs", catalogs_index_api, name="catalogs_index_api"),
    path("api/catalogs/", catalogs_index_api),
    path("api/collections", collections_index_api, name="collections_index_api"),
    path("api/collections/", collections_index_api),
    path("api/collections-page", collections_index_api),
    path("api/collections-page/", collections_index_api),
    path("api/renovations", renovation_index_api, name="renovation_index_api"),
    path("api/renovations/", renovation_index_api),
    path("api/products", product_detail_api, name="product_detail_api"),
    path("api/products/", product_detail_api),
    path("api/collections/product", product_detail_api),
    path("api/collections/product/", product_detail_api),
    path("api/contact-page", contact_page_api, name="contact_page_api"),
    path("api/contact-page/", contact_page_api),
    path("api/contact-us", contact_page_api),
    path("api/contact-us/", contact_page_api),
    path("search/", search_views.search, name="search"),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
]
