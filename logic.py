import time
import traceback as tb

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from submission import models as sm_models
from utils.logger import get_logger

from plugins.doaj_transporter import clients, models

logger = get_logger(__name__)


def check_debug_settings():
    if settings.DEBUG:
        if hasattr(settings, 'DOAJ_PUSH_ON_DEBUG'):
            return settings.DOAJ_PUSH_ON_DEBUG
        return False
    return True


def push_article_to_doaj(article):
    """ Updates or creates a record in DOAJ for the given article
    :param article: submission.models.Article
    """
    doi = article.get_identifier("doi")
    if not doi:
        logger.warning("Pushing article to DOAJ without a DOI")

    if check_debug_settings():
        article_client = clients.DOAJArticle.from_article_model(article)
        article_client.upsert()
        return article_client.id
    encoded = encode_article_to_doaj_json(article)
    logger.debug("Ignoring DOAJ upsert on DEBUG mode")
    logger.debug(encoded)
    return encoded


def push_issue_to_doaj(issue, raise_on_error=True):
    errors = {}
    for article in issue.articles.filter(
        stage=sm_models.STAGE_PUBLISHED,
    ):
        if article.date_published:
            try:
                push_article_to_doaj(article)
                logger.info("Sleeping thread for 200ms")
                time.sleep(0.2)
            except Exception as e:
                if raise_on_error:
                    raise
                errors[article.pk] = e
                logger.error(
                    "[DOAJ] Error pushing article %s of issue %s",
                    article.pk, issue
                )
                tb.print_exc()
    return errors


def encode_article_to_doaj_json(article):
    article_client = clients.DOAJArticle.from_article_model(article)
    return article_client.encode()


def delete_article_from_doaj(doaj_id):
    """ Deletes an article from DOAJ as well as the local identifier
    :param doaj_id: identifiers.models.Identifier
    """
    if check_debug_settings():
        article_client = clients.DOAJArticle.from_article_model(
            doaj_id.article)
        article_client.delete()
        doaj_id.delete()
    else:
        logger.debug("Ignoring DOAJ delete on DEBUG mode")
