from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError
from wagtail.models import Locale, Page

from terms_cms.models import TermItem, TermsPage


TERMS_COPY = {
    "en": {
        "title": "Terms & Conditions",
        "intro_heading": "Terms and Conditions",
        "intro_body": "Please review these terms and conditions before using this website.",
        "search_description": "Terms and conditions page",
        "terms": [
            {
                "key": "scope-and-acceptance",
                "title": "Scope and Acceptance",
                "body": "By accessing this website, you acknowledge and accept these terms.",
            },
            {
                "key": "intellectual-property",
                "title": "Intellectual Property",
                "body": "All content and assets on this website are protected by applicable law.",
            },
            {
                "key": "limitations-of-liability",
                "title": "Limitations of Liability",
                "body": "Policrafters is not liable for indirect damages resulting from use of this website.",
            },
            {
                "key": "third-party-links",
                "title": "Third-Party Links",
                "body": "External links are provided for reference; their content is outside our control.",
            },
            {
                "key": "product-information",
                "title": "Product Information",
                "body": "Specifications, finishes, and availability may change without prior notice.",
            },
            {
                "key": "privacy-and-data",
                "title": "Privacy and Data",
                "body": "Any personal data provided is processed according to our privacy practices.",
            },
            {
                "key": "updates-to-these-terms",
                "title": "Updates to These Terms",
                "body": "These terms may be updated periodically; the latest version applies.",
            },
        ],
    },
    "es": {
        "title": "Términos y Condiciones",
        "intro_heading": "Términos y Condiciones",
        "intro_body": "Por favor revise estos términos y condiciones antes de usar este sitio web.",
        "search_description": "Página de términos y condiciones",
        "terms": [
            {
                "key": "scope-and-acceptance",
                "title": "Alcance y Aceptación",
                "body": "Al acceder a este sitio, usted reconoce y acepta estos términos.",
            },
            {
                "key": "intellectual-property",
                "title": "Propiedad Intelectual",
                "body": "Todo el contenido y recursos de este sitio están protegidos por la ley aplicable.",
            },
            {
                "key": "limitations-of-liability",
                "title": "Limitación de Responsabilidad",
                "body": "Policrafters no se hace responsable por daños indirectos derivados del uso del sitio.",
            },
            {
                "key": "third-party-links",
                "title": "Enlaces de Terceros",
                "body": "Los enlaces externos se ofrecen como referencia; su contenido está fuera de nuestro control.",
            },
            {
                "key": "product-information",
                "title": "Información de Producto",
                "body": "Especificaciones, acabados y disponibilidad pueden cambiar sin previo aviso.",
            },
            {
                "key": "privacy-and-data",
                "title": "Privacidad y Datos",
                "body": "Los datos personales compartidos se procesan de acuerdo con nuestras prácticas de privacidad.",
            },
            {
                "key": "updates-to-these-terms",
                "title": "Actualizaciones de Estos Términos",
                "body": "Estos términos pueden actualizarse periódicamente; aplica siempre la versión más reciente.",
            },
        ],
    },
}


class Command(BaseCommand):
    help = "Create or update TermsPage content in EN/ES for fast QA and previews."

    def add_arguments(self, parser):
        parser.add_argument(
            "--lang",
            choices=["en", "es", "both"],
            default="both",
            help="Which locale to seed. Default: both.",
        )
        parser.add_argument(
            "--slug",
            default="terms-and-conditions",
            help="Slug to use when creating new pages. Default: terms-and-conditions.",
        )
        parser.add_argument(
            "--draft",
            action="store_true",
            help="Leave page(s) as draft instead of publishing.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print planned operations without writing changes.",
        )

    def handle(self, *args, **options):
        lang_option = options["lang"]
        slug = options["slug"]
        draft_only = options["draft"]
        dry_run = options["dry_run"]

        target_langs = ["en", "es"] if lang_option == "both" else [lang_option]
        root_page = Page.get_first_root_node()

        def find_page_for_locale(locale_obj, parent_page, page_slug, preferred_translation_key=None):
            locale_qs = TermsPage.objects.filter(locale=locale_obj)

            if preferred_translation_key is not None:
                translated_page = locale_qs.filter(
                    translation_key=preferred_translation_key
                ).order_by("-pk").first()
                if translated_page is not None:
                    return translated_page

            page = (
                locale_qs.child_of(parent_page)
                .filter(slug=page_slug)
                .order_by("-pk")
                .first()
            )
            if page is not None:
                return page

            page = locale_qs.filter(slug=page_slug).order_by("-pk").first()
            if page is not None:
                return page

            page = locale_qs.child_of(parent_page).order_by("-pk").first()
            if page is not None:
                return page

            return locale_qs.order_by("-pk").first()

        en_page_for_linking = TermsPage.objects.filter(
            locale__language_code="en"
        ).filter(slug=slug).order_by("-pk").first()

        for lang in target_langs:
            locale, _ = Locale.objects.get_or_create(language_code=lang)
            copy = TERMS_COPY[lang]
            try:
                if lang == "en":
                    page = find_page_for_locale(locale, root_page, slug)
                else:
                    if en_page_for_linking is None:
                        en_page_for_linking = (
                            TermsPage.objects.filter(locale__language_code="en")
                            .filter(slug=slug)
                            .order_by("-pk")
                            .first()
                        )
                    if en_page_for_linking is None:
                        raise CommandError(
                            "No English TermsPage found. Create EN first or run seed with --lang both."
                        )

                    page = (
                        TermsPage.objects.filter(locale=locale)
                        .filter(translation_key=en_page_for_linking.translation_key)
                        .order_by("-pk")
                        .first()
                    )
            except (ProgrammingError, OperationalError) as exc:
                raise CommandError(
                    "Terms CMS tables are not available yet. Run migrations first: "
                    "'python manage.py migrate'"
                ) from exc

            action = "Updating" if page else "Creating"
            self.stdout.write(
                f"{action} TermsPage for locale '{lang}' under parent 'root' "
                f"(dry_run={str(dry_run).lower()})"
            )

            if dry_run:
                planned_slug = slug if lang == "en" else "(translation from EN)"
                self.stdout.write(
                    f"  -> title='{copy['title']}', slug='{planned_slug}', terms={len(copy['terms'])}"
                )
                continue

            if page is None:
                if lang == "en":
                    page_slug = slug
                    if root_page.get_children().filter(slug=page_slug).exists():
                        page_slug = f"{slug}-{lang}"

                    page = TermsPage(
                        title=copy["title"],
                        slug=page_slug,
                        locale=locale,
                        intro_heading=copy["intro_heading"],
                        intro_body=copy["intro_body"],
                        search_description=copy["search_description"],
                    )
                    root_page.add_child(instance=page)
                else:
                    page = en_page_for_linking.copy_for_translation(locale)
                    if isinstance(page, Page):
                        page = page.specific

            actual_lang = getattr(getattr(page, "locale", None), "language_code", None)
            if actual_lang != lang:
                raise CommandError(
                    f"Seed language mismatch: requested '{lang}' but resolved page locale is "
                    f"'{actual_lang}' (page id={page.id}). Aborting to avoid cross-locale overwrite."
                )

            page.title = copy["title"]
            page.intro_heading = copy["intro_heading"]
            page.intro_body = copy["intro_body"]
            page.search_description = copy["search_description"]
            page.save()

            existing_items = {}
            duplicate_items = []
            for item in page.term_items.all().order_by("key", "sort_order", "pk"):
                if item.key in existing_items:
                    duplicate_items.append(item)
                    continue
                existing_items[item.key] = item

            for duplicate in duplicate_items:
                duplicate.delete()

            incoming_keys = set()
            for index, term in enumerate(copy["terms"]):
                term_key = term["key"]
                incoming_keys.add(term_key)
                item = existing_items.get(term_key)

                if item is None:
                    TermItem.objects.create(
                        page=page,
                        locale=page.locale,
                        key=term_key,
                        title=term["title"],
                        body=term["body"],
                        sort_order=index,
                    )
                    continue

                item.title = term["title"]
                item.body = term["body"]
                item.sort_order = index
                if item.locale_id != page.locale_id:
                    item.locale = page.locale
                item.save()

            stale_items = page.term_items.exclude(key__in=incoming_keys)
            stale_items_count = stale_items.count()
            if stale_items_count:
                stale_items.delete()

            if not draft_only:
                page.save_revision().publish()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  -> Published page id={page.id} locale={actual_lang} "
                        f"title='{page.title}' with {len(copy['terms'])} terms"
                    )
                )
            else:
                page.save_revision()
                self.stdout.write(
                    self.style.WARNING(
                        f"  -> Saved draft page id={page.id} locale={actual_lang} "
                        f"title='{page.title}' with {len(copy['terms'])} terms"
                    )
                )

            if lang == "en":
                en_page_for_linking = page

        self.stdout.write(self.style.SUCCESS("Seed completed."))
