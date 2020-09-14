import datetime
import os
from unittest import mock

from core import models as core_models
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from journal.models import Journal, Issue
from press.models import Press
from submission.models import Article, FrozenAuthor, Licence
from submission.models import FrozenAuthor
from utils.testing import helpers
from utils import install

from doaj_transporter.client import DOAJArticle, ArticleSearchClient


class MockResponse(mock.Mock):
    def __init__(self, content=None, ok=True):
        self.content = content or ""
        self._ok = ok

    @property
    def text(self):
        return self.content

    @property
    def ok(self):
        return self._ok


class TestDOAJArticleClient(TestCase):
    def setUp(self):
        press = helpers.create_press()
        self.journal, _ = helpers.create_journals()
        self.journal.save()
        call_command('load_default_settings', management_command=False)
        self.journal.publisher = "doaj"
        self.journal.code = "doaj"
        self.journal.save()

        install.update_license(self.journal, management_command=False)

        self.article = self._create_article(
            date_published=datetime.date(day=1, month=7,year=2019))
        self.encoded_article = """
        {
        "admin": {
            "publisher_record_id": null
        },
        "bibjson":{
            "identifier":[
                {
                    "id":"0000-0000",
                    "type":"eissn"
                },
                {
                    "id": null,
                    "type": "doi"
                }
            ],
            "author":[
                {
                    "name":"Testla Musketeer",
                    "affiliation":"OLH"
                }
            ],
            "journal":{
                "volume":"1",
                "license":[
                    {
                    "title":"All rights reserved",
                    "url":"https://creativecommons.org/licenses/authors",
                    "open_access":true
                    }
                ],
                "publisher":"doaj",
                "title":"Journal One",
                "number":"1",
                "language":[
                    "en"
                ]
            },
            "keywords":[

            ],
            "year":2019,
            "month":7,
            "subject": null,
            "title":"The art of writing test titles",
            "link":[
                {
                    "url":"http://localhost/doaj/article/id/%s/",
                    "content_type":"text/html",
                    "type":"fulltext"
                }
            ],
            "abstract":"The test abstract"
            }
        }
        """ % (self.article.pk)

    def _create_article(self, **kwargs):
        kwargs.setdefault("abstract", "The test abstract")
        kwargs.setdefault("title", "The art of writing test titles")
        kwargs.setdefault("date_published", timezone.now())
        kwargs.setdefault("journal", self.journal)
        article = Article(**kwargs)
        article.save()

        author = helpers.create_user("author@doaj.com")
        author.first_name = "Testla"
        author.last_name = "Musketeer"
        author.institution = "OLH"
        author.save()
        article.authors.add(author)
        article.owner = author

        issue = Issue.objects.create(
            journal=self.journal,
            volume=1,
            issue=1,
        )
        article.primary_issue = issue

        article.license = Licence.objects.all()[0]

        _file = core_models.File.objects.create(
            mime_type="A/FILE",
            original_filename="test.pdf",
            uuid_filename="UUID",
            label="A file",
            description="Oh yes, it's a file",
            owner=author,
            is_galley=True,
            privacy="owner"
        )
        pdf_galley = core_models.Galley.objects.create(
            article=article,
            file=_file,
            label='PDF'
        )
        article.galley_set.add(pdf_galley)
        article.save()
        article.snapshot_authors(article)
        return article

    @override_settings(DOAJ_API_TOKEN="dummy_key")
    def test_client_from_article_model(self):
        article = self.article
        doaj_article = DOAJArticle.from_article_model(article)

        self.assertEqual(article.title, doaj_article.title)

    @override_settings(DOAJ_API_TOKEN="dummy_key")
    def test_encode_article(self):
        doaj_article = DOAJArticle.from_article_model(self.article)
        result = doaj_article.encode()
        self.maxDiff = None
        self.assertJSONEqual(result, self.encoded_article)

    @override_settings(DOAJ_API_TOKEN="dummy_key")
    def test_decode_article(self):
        expected = DOAJArticle.from_article_model(self.article)
        result = DOAJArticle(api_token=settings.DOAJ_API_TOKEN)
        result._decode(self.encoded_article)
        for a,b,c in zip(DOAJArticle.__slots__, expected, result):
            print(a,b, c)
        self.assertEqual(expected, result)



class TestArticleSearch(TestCase):
    def test_search(self):
        response_data = """
        {
            "admin": {
                "in_doaj": true
            },
            "last_updated": "2019-02-21T14:22:52Z",
            "id": "mock_id",
            "bibjson": {
                "identifier": [
                {
                    "type": "doi",
                    "id": "10.001/mock.01"
                },
                {
                    "type": "eissn",
                    "id": "0000-0000"
                }
                ],
            },
            "created_date": "2016-10-31T15:38:29Z"
        }"""
        mock_response = MockResponse(response_data)
        mock_requests = mock.MagicMock(return_value=mock_response)
        with mock.patch("doaj.client.requests", mock_requests):
            client = ArticleSearchClient()
            client.search("10.001/mock.01")
            self.assertTrue(client.one().in_doaj)

