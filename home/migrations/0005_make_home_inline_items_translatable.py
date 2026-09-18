# Generated manually to support Wagtail Localize inline item translation
import uuid

import django.db.models.deletion
from django.db import migrations, models


def set_inline_item_locale(apps, schema_editor):
    Locale = apps.get_model("wagtailcore", "Locale")
    default_locale = Locale.objects.order_by("id").first()
    if default_locale is None:
        return

    model_names = [
        "HomeFeaturedProjectItem",
        "HomeTeamMemberItem",
        "HomeValueSlideItem",
        "HomeCatalogItem",
        "HomeContactLinkItem",
    ]

    for model_name in model_names:
        model = apps.get_model("home", model_name)
        for item in model.objects.select_related("page", "page__locale").all():
            page_locale_id = getattr(item.page, "locale_id", None)
            item.locale_id = page_locale_id or default_locale.id
            item.translation_key = uuid.uuid4()
            item.save(update_fields=["locale", "translation_key"])


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailcore", "0053_locale_model"),
        ("home", "0004_remove_homepage_catalogs_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="homecatalogitem",
            name="locale",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AddField(
            model_name="homecatalogitem",
            name="translation_key",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="homecontactlinkitem",
            name="locale",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AddField(
            model_name="homecontactlinkitem",
            name="translation_key",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="homefeaturedprojectitem",
            name="locale",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AddField(
            model_name="homefeaturedprojectitem",
            name="translation_key",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="hometeammemberitem",
            name="locale",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AddField(
            model_name="hometeammemberitem",
            name="translation_key",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="homevalueslideitem",
            name="locale",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AddField(
            model_name="homevalueslideitem",
            name="translation_key",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(set_inline_item_locale, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="homecatalogitem",
            name="locale",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AlterField(
            model_name="homecatalogitem",
            name="translation_key",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AlterField(
            model_name="homecontactlinkitem",
            name="locale",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AlterField(
            model_name="homecontactlinkitem",
            name="translation_key",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AlterField(
            model_name="homefeaturedprojectitem",
            name="locale",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AlterField(
            model_name="homefeaturedprojectitem",
            name="translation_key",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AlterField(
            model_name="hometeammemberitem",
            name="locale",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AlterField(
            model_name="hometeammemberitem",
            name="translation_key",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AlterField(
            model_name="homevalueslideitem",
            name="locale",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AlterField(
            model_name="homevalueslideitem",
            name="translation_key",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AddConstraint(
            model_name="homecatalogitem",
            constraint=models.UniqueConstraint(fields=("translation_key", "locale"), name="homecatalogitem_translation_key_locale_uniq"),
        ),
        migrations.AddConstraint(
            model_name="homecontactlinkitem",
            constraint=models.UniqueConstraint(fields=("translation_key", "locale"), name="homecontactlinkitem_translation_key_locale_uniq"),
        ),
        migrations.AddConstraint(
            model_name="homefeaturedprojectitem",
            constraint=models.UniqueConstraint(fields=("translation_key", "locale"), name="homefeaturedprojectitem_translation_key_locale_uniq"),
        ),
        migrations.AddConstraint(
            model_name="hometeammemberitem",
            constraint=models.UniqueConstraint(fields=("translation_key", "locale"), name="hometeammemberitem_translation_key_locale_uniq"),
        ),
        migrations.AddConstraint(
            model_name="homevalueslideitem",
            constraint=models.UniqueConstraint(fields=("translation_key", "locale"), name="homevalueslideitem_translation_key_locale_uniq"),
        ),
    ]
