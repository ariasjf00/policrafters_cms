from django import template

from policrafters_cms.middleware import add_locale_to_url


register = template.Library()


@register.filter
def add_locale_query(url, locale_code):
    return add_locale_to_url(url, locale_code)