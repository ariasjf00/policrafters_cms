import logging
from pathlib import Path

from django.conf import settings
from django.dispatch import receiver
from wagtail.signals import page_published

logger = logging.getLogger(__name__)


@receiver(page_published)
def trigger_astro_rebuild(sender, instance, **kwargs):
    """
    Genera una señal para que el host solicite el rebuild de Astro
    cuando se publica una página en Wagtail.

    Django/Wagtail no ejecuta Docker ni el deploy directamente.
    """
    trigger_file = Path(
        getattr(
            settings,
            "ASTRO_DEPLOY_TRIGGER_FILE",
            "/deploy-trigger/astro-rebuild",
        )
    )

    try:
        trigger_file.parent.mkdir(parents=True, exist_ok=True)
        trigger_file.touch()

        logger.info(
            "Astro rebuild requested after publishing page %s (id=%s)",
            instance,
            instance.pk,
        )

    except OSError:
        logger.exception(
            "Unable to create Astro rebuild trigger: %s",
            trigger_file,
        )