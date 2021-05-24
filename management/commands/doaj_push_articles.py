import time
import traceback as tb

from django.core.management.base import BaseCommand
from submission.models import Article, STAGE_PUBLISHED

from plugins.doaj_transporter import clients, logic, synch


class Command(BaseCommand):

    help = "Pushes articles to DOAJ for given journal, issue or articles list"

    def add_arguments(self, parser):
        parser.add_argument('--issue_id', '-i')
        parser.add_argument('--journal_code', '-j')
        parser.add_argument('--article_ids', '-a,', nargs="+", type=int)
        parser.add_argument('--dry_run', action="store_true", default=False)

    def handle(self, *args, **options):
        articles = Article.objects.none()
        if options.get("journal_code"):
            articles |= Article.objects.filter(journal__code=options["journal_code"])
        if options.get("article_ids"):
            articles |= Article.objects.filter(id__in=options["article_ids"])
        if options.get("issue_id"):
            articles |= Article.objects.filter(issues__id=options["article_ids"])

        if articles.count() < 1:
            self.stderr.write("No articles found with given parameters")

        for article in articles.filter(
            stage=STAGE_PUBLISHED,
            date_publised__isnull=False,
        ):
            print("[%s] Handling article %s" % (article.pk, article))
            doi = article.get_doi()
            if doi:
                # If we have a DOI check if article has been synched first
                synch.synch_article_from_janeway(article)
            if options["dry_run"]:
                print(logic.encode_to_doaj_json(article))
            else:
                try:
                    logic.push_article_to_doaj(article)
                    print("Sleeping thread for 200ms")
                    time.sleep(0.2)
                except Exception as e:
                    self.stderr.write("[%s] Failed to push:" % article.pk)
                    err = e
                    tb.print_exc()
