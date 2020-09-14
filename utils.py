import os
import uuid
import shutil

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.template.loader import render_to_string

from core import files, models as core_models
from journal import models
from submission import models as submission_models



def prepare_temp_folder(request, issue=None, article=None):
    """
    Perpares a temp folder to store files for zipping
    :param issue: Issue Object
    :param article: Article object
    :return: Folder path, string
    """
    folder_string = str(uuid.uuid4())

    if article and issue:
        folder_string = '{journal_code}_{vol}_{issue}_{pk}'.format(
            journal_code=request.journal.code,
            vol=issue.volume,
            issue=issue.issue,
            pk=article.pk)
    elif issue:
        folder_string = '{journal_code}_{vol}_{issue}_{year}'.format(
            journal_code=request.journal.code,
            vol=issue.volume,
            issue=issue.issue,
            year=issue.date.year)

    folder = os.path.join(settings.BASE_DIR, 'files', 'temp', folder_string)
    files.mkdirs(folder)

    return folder, folder_string


def zip_folder(temp_folder):
    shutil.make_archive(temp_folder, 'zip', temp_folder)
    shutil.rmtree(temp_folder)



def prepare_export_for_article(request):
    """
    Prepares a single article for export
    :param request: HttpRequest
    :return: Streaming zip file
    """
    article_id = request.POST.get('export-article')
    article = get_object_or_404(submission_models.Article, pk=article_id, journal=request.journal)

    issue = article.primary_issue if article.primary_issue else article.issue
    temp_folder, folder_string = prepare_temp_folder(request, issue=issue, article=article)
    prepare_article(request, article, temp_folder, article_only=True)
    zip_folder(temp_folder)

    return files.serve_temp_file('{folder}.zip'.format(folder=temp_folder),
                                 '{filename}.zip'.format(filename=folder_string))


def get_articles(request):
    """
    Returns a QuerySet of articles suitable for export
    :param request: HttpRequest
    :return: QuerySet of articles
    """
    return submission_models.Article.objects.filter(date_published__isnull=False,
                                                    stage=submission_models.STAGE_PUBLISHED,
                                                    journal=request.journal)
