from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from utils.logger import get_logger

from plugins.doaj_transporter import clients, models

logger = get_logger(__name__)


def push_article_to_doaj(article):
    """ Updates or creates a record in DOAJ for the given article
    :param article: submission.models.Article
    """
    doi = article.get_identifier("doi")
    if not doi:
        logger.warning("Pushing article to DOAJ without a DOI")

    article_client = clients.DOAJArticle.from_article_model(article)
    article_client.upsert()

    return article_client.id


def delete_article_from_doaj(doaj_id):
    """ Deletes an article from DOAJ as well as the local identifier
    :param doaj_id: identifiers.models.Identifier
    """
    article_client = clients.DOAJArticle.from_doaj_id(
        doaj_id.identifier)
    article_client.delete()
    doaj_id.delete()
