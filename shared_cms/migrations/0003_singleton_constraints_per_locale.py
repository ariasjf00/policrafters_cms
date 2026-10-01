from django.db import migrations, models


def dedupe_singleton_blocks(apps, schema_editor):
    DirectContactBlock = apps.get_model("shared_cms", "DirectContactBlock")
    BrandsHeaderBlock = apps.get_model("shared_cms", "BrandsHeaderBlock")

    for Model in (DirectContactBlock, BrandsHeaderBlock):
        locale_ids = (
            Model.objects.values_list("locale_id", flat=True)
            .order_by()
            .distinct()
        )
        for locale_id in locale_ids:
            duplicates = Model.objects.filter(locale_id=locale_id).order_by("-pk")
            if duplicates.count() <= 1:
                continue
            keep = duplicates.first()
            Model.objects.filter(locale_id=locale_id).exclude(pk=keep.pk).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("shared_cms", "0002_brandsheaderblock_brandsheaderlogoitem"),
    ]

    operations = [
        migrations.RunPython(dedupe_singleton_blocks, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="directcontactblock",
            constraint=models.UniqueConstraint(
                fields=("translation_key", "locale"),
                name="unique_translation_key_locale_shared_cms_directcontactblock",
            ),
        ),
        migrations.AddConstraint(
            model_name="directcontactblock",
            constraint=models.UniqueConstraint(
                fields=("locale",),
                name="unique_directcontactblock_locale",
            ),
        ),
        migrations.AddConstraint(
            model_name="brandsheaderblock",
            constraint=models.UniqueConstraint(
                fields=("translation_key", "locale"),
                name="unique_translation_key_locale_shared_cms_brandsheaderblock",
            ),
        ),
        migrations.AddConstraint(
            model_name="brandsheaderblock",
            constraint=models.UniqueConstraint(
                fields=("locale",),
                name="unique_brandsheaderblock_locale",
            ),
        ),
    ]
