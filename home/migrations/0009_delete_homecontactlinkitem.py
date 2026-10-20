from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0008_alter_homepage_hero_video_horizontal_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="HomeContactLinkItem",
        ),
    ]
