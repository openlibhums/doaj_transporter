"""
This module contains utilities for synchronising state between DOAJ and the
Janeway instance
"""
__copyright__ = "Copyright 2020 Birkbeck, University of London"
__author__ = "Birkbeck Centre for Technology and Publishing"
__license__ = "AGPL v3"
__maintainer__ = "Birkbeck Centre for Technology and Publishing"

import time

from identifiers.models import Identifier
from journal import models as journal_models
from utils.logger import get_logger

from plugins.doaj_transporter import (
    clients,
    exceptions,
    models,
    plugin_settings,
)

logger = get_logger(__name__)


def synch_all_from_doaj(journal=None):
    """ Synchs DOAJ records into Janeway
    """
    api_token = plugin_settings.DOAJ_API_TOKEN
    if journal:
        journals = [journal]
    else:
        journals = journal_models.Journal.objects.all()
    for journal in journals:
        search_client = clients.ArticleSearchClient(api_token)
        if journal.publisher:
            results = search_client.search_by_publisher(journal.publisher)
            for result in results:
                created = synch_result_from_doaj(result)
        logger.info("Sleeping thread for 100ms")
        time.sleep(0.1)


def synch_result_from_doaj(search_result):
    """ Synch a single DOAJ Article record into Janeway
    The DOAJ result must match an article in Janeway by DOI. The record
    created is an instance of models.DOAJRecord. Importing actual articles
    into Janeway is not supported due to the difficulties when matching the
    journals (only possible by either title or ISSN)

    :param search_result: An instance of ArticleSearchResult
    :return: A Bool indicated if a record has been created
    """
    created = False
    if search_result.doi:
        try:
            doi = Identifier.objects.get(
                id_type="doi", identifier=search_result.doi)
            o, created = models.DOAJArticle.objects.get_or_create(
                article=doi.article,
                doaj_id=search_result.id,
            )
            if created:
                logger.debug("Matched %s to %s", search_result, o.article)
                logger.info(
                    "Matched %s to article %s", search_result.id, o.article.pk)
        except Identifier.DoesNotExist:
            logger.info("No article found for DOI %s", search_result.doi)
    return created


def synch_all_from_janeway(journal=None, push=False):
    """ Downloads DOAJ records for articles existing in the Janeway install
    Articles are looked up by DOI
    :param journal: an instance of janeway.models.Journal
    :param push (bool): Whether or not to push missing records to DOAJ
    :return: A list of article PKs of those articles that have been synched
    """
    if journal:
        journals = [journal]
    else:
        journals = journal_models.Journal.objects.all()
    for journal in journals:
        for article in journal.article_set.filter(stage="Published"):
            doi = article.get_doi()
            if doi:
                obj, c = synch_article_from_janeway(article)
                if push:
                    logic.push_article_to_doaj(article)
                logger.info("Thread Sleeping for 250ms")
                time.sleep(0.25)


def synch_article_from_janeway(article):
    """ Downloads DOAJ record for an article in Janeway
    :param article: an instance of janeway.models.Article
    :return: A tuple with the local record and bool flagging its creation
    """
    doi = article.get_doi()
    api_token = plugin_settings.DOAJ_API_TOKEN
    created = obj = None
    try:
        models.DOAJArticle.objects.get(article=article)
    except models.DOAJArticle.DoesNotExist:
        search_client = clients.ArticleSearchClient(api_token)
        results = search_client.search_by_doi(doi)
        try:
            doaj_id = next(results).id
            obj, created = models.DOAJArticle.objects.get_or_create(
                article=article,
                doaj_id=doaj_id,
            )
            if created:
                logger.info("New DOAJ record for article %s ", article.pk)

        except StopIteration:
            logger.info("Article %s is not on DOAJ", article.pk)
    return obj, created
