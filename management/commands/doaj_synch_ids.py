import time

from django.core.management.base import BaseCommand
from journal.models import Journal
from submission.models import Article

from plugins.doaj_transporter import clients, logic, synch


class Command(BaseCommand):
    """ Synchronise DOAJ IDs with your Janeway journal"""


    help = "Synchronise DOAJ IDs with your Janeway journal"

    def add_arguments(self, parser):
        parser.add_argument('journal_code')

    def handle(self, *args, **options):
        journal = Journal.objects.get(code=options["journal_code"])
        articles = Article.objects.filter(journal=journal)

        if articles.count() < 1:
            self.stderr.write("No articles found with given parameters")

        print("Searching Janeway articles in DOAJ by DOI...")
        for article in articles:
            doi = article.get_doi()
            if doi:
                print("[%s:%s] Handling article %s" % (
                    article.journal.code, article.pk, article)
            )
                synch.synch_article_from_janeway(article)

        print("Searching Janeway articles in DOAJ by DOI...")
        synch.synch_all_from_doaj(journal)
