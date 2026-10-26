from django.utils.translation import gettext_lazy as _

from wagtail.images.forms import BaseImageForm


class RequiredAltTextImageForm(BaseImageForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        description_field = self.fields["description"]
        description_field.required = True
        description_field.label = _("Alternative text (alt)")
        description_field.help_text = _(
            "Describe the image for accessibility and search engines."
        )
