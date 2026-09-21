from django.db import models
from django.shortcuts import render
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable
from wagtail.models import Page
from wagtail.models import TranslatableMixin


class HomePage(Page):
    hero_video_horizontal = models.URLField(blank=True)
    hero_video_vertical = models.URLField(blank=True)

    hero_eyebrow = models.CharField(max_length=255, blank=True)
    hero_heading = models.CharField(max_length=255, blank=True)
    hero_cta = models.CharField(max_length=120, blank=True)

    projects_eyebrow = models.CharField(max_length=255, blank=True)
    projects_heading = models.CharField(max_length=255, blank=True)
    projects_cta = models.CharField(max_length=120, blank=True)
    projects_prev_aria = models.CharField(max_length=255, blank=True)
    projects_next_aria = models.CharField(max_length=255, blank=True)
    projects_carousel_aria = models.CharField(max_length=255, blank=True)
    projects_dot_aria = models.CharField(max_length=255, blank=True)

    about_eyebrow = models.CharField(max_length=255, blank=True)
    about_heading = models.CharField(max_length=255, blank=True)
    about_body_1 = models.TextField(blank=True)
    about_body_2 = models.TextField(blank=True)
    about_brands_label = models.CharField(max_length=255, blank=True)
    about_cta = models.CharField(max_length=120, blank=True)

    team_eyebrow = models.CharField(max_length=255, blank=True)
    team_heading = models.CharField(max_length=255, blank=True)

    values_eyebrow = models.CharField(max_length=255, blank=True)
    values_heading = models.CharField(max_length=255, blank=True)
    values_prev_aria = models.CharField(max_length=255, blank=True)
    values_next_aria = models.CharField(max_length=255, blank=True)
    values_carousel_aria = models.CharField(max_length=255, blank=True)
    values_dot_aria = models.CharField(max_length=255, blank=True)

    contact_heading = models.CharField(max_length=255, blank=True)
    contact_cta = models.CharField(max_length=120, blank=True)

    hero_image_horizontal = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    hero_image_vertical = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    site_logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    def serve_preview(self, request, mode_name):
        from home.api import serialize_home_page

        lang = getattr(
            getattr(self, "locale", None),
            "language_code",
            "en",
        )

        # DEBUG TEMPORAL
        print("\n===== WAGTAIL PREVIEW DEBUG =====")
        print("PAGE:", self.pk)
        print("TEAM:", self.team_members_items.count())
        print("PROJECTS:", self.featured_projects_items.count())

        for item in self.featured_projects_items.all():
            print(
                "PROJECT:",
                item.pk,
                getattr(item, "title", None),
            )

        print("===============================\n")

        data = serialize_home_page(
            self,
            request,
            lang,
        )

        return render(
            request,
            "home/astro_preview.html",
            {
                "preview_data": data,
                "preview_lang": lang,
            },
        )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("hero_eyebrow"),
                FieldPanel("hero_heading"),
                FieldPanel("hero_cta"),
                FieldPanel("hero_video_horizontal"),
                FieldPanel("hero_video_vertical"),
                FieldPanel("hero_image_horizontal"),
                FieldPanel("hero_image_vertical"),
                FieldPanel("site_logo"),
            ],
            heading="Hero",
        ),
        MultiFieldPanel(
            [
                FieldPanel("projects_eyebrow"),
                FieldPanel("projects_heading"),
                FieldPanel("projects_cta"),
                FieldPanel("projects_prev_aria"),
                FieldPanel("projects_next_aria"),
                FieldPanel("projects_carousel_aria"),
                FieldPanel("projects_dot_aria"),
            ],
            heading="Projects copy",
        ),
        MultiFieldPanel(
            [
                FieldPanel("about_eyebrow"),
                FieldPanel("about_heading"),
                FieldPanel("about_body_1"),
                FieldPanel("about_body_2"),
                FieldPanel("about_brands_label"),
                FieldPanel("about_cta"),
            ],
            heading="About copy",
        ),
        MultiFieldPanel(
            [
                FieldPanel("team_eyebrow"),
                FieldPanel("team_heading"),
            ],
            heading="Team copy",
        ),
        MultiFieldPanel(
            [
                FieldPanel("values_eyebrow"),
                FieldPanel("values_heading"),
                FieldPanel("values_prev_aria"),
                FieldPanel("values_next_aria"),
                FieldPanel("values_carousel_aria"),
                FieldPanel("values_dot_aria"),
            ],
            heading="Values copy",
        ),
        MultiFieldPanel(
            [
                FieldPanel("contact_heading"),
                FieldPanel("contact_cta"),
            ],
            heading="Contact copy",
        ),
        InlinePanel("featured_projects_items", label="Featured projects"),
        InlinePanel("team_members_items", label="Team members"),
        InlinePanel("values_slide_items", label="Values slides"),
        InlinePanel("contact_link_items", label="Contact links"),
    ]


class HomeFeaturedProjectItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "home.HomePage",
        related_name="featured_projects_items",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150)
    thumbnail = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    description = models.TextField(blank=True)

    panels = [
        FieldPanel("title"),
        FieldPanel("slug"),
        FieldPanel("thumbnail"),
        FieldPanel("description"),
    ]


class HomeTeamMemberItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "home.HomePage",
        related_name="team_members_items",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=150, blank=True)
    photo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    bio = models.TextField(blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("role"),
        FieldPanel("photo"),
        FieldPanel("bio"),
    ]


class HomeValueSlideItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "home.HomePage",
        related_name="values_slide_items",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=150)
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    description = models.TextField(blank=True)

    panels = [
        FieldPanel("title"),
        FieldPanel("image"),
        FieldPanel("description"),
    ]


class HomeContactLinkItem(TranslatableMixin, Orderable):
    page = ParentalKey(
        "home.HomePage",
        related_name="contact_link_items",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    url = models.URLField()

    panels = [
        FieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("url"),
    ]
