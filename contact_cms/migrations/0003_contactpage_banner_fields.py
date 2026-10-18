from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("contact_cms", "0002_contactpage_project_button_label_and_more"),
        ("wagtailimages", "0027_image_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="contactpage",
            name="banner_eyebrow",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="contactpage",
            name="banner_heading",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="contactpage",
            name="banner_image",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.image",
            ),
        ),
    ]
