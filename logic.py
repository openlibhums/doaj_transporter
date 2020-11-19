from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from doaj_transporter import clients, models

def push_article_to_doaj(article):
    """ Updates or creates a record in DOAJ for the given article
    :param article: submission.models.Article
    """
    try:
        doaj_record = article.doajarticle
    except ObjectDoesNotExist:
        doaj_record = None

    article_client = clients.DOAJArticle.from_article_model(article)
    article_client.upsert()
    if not doaj_record:
        doaj_record = models.DOAJArticle.objects.create(
            article=article,
            doaj_id=article_client.id,
        )

    doaj_record.last_updated = timezone.now()
    doaj_record.save()

    return doaj_record


def delete_article_from_doaj(doaj_record):
    """ Deletes an articlefrom DOAJ as well as the local record
    :param doaj_article: doaj_transporter.models.Article
    """
    article_client = clients.DOAJArticle.from_doaj_record(doaj_record)
    article_client.delete()
    doaj_record.delete()


