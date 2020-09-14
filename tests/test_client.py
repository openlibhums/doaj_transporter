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
from utils.testing.helpers import create_user
from utils import install

from doaj.client import DOAJArticle, ArticleSearchClient


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
        press = Press.objects.create()
        self.journal = Journal(code="doaj", domain="doaj")
        self.journal.save()
        call_command('load_default_settings', management_command=False)
        self.journal.publisher = "doaj"
        self.journal.save()

        install.update_license(self.journal, management_command=False)

        self.article = self._create_article()
        self.encoded_article = """
        {
        "bibjson":{
            "identifier":[
                {
                    "id":"0000-0000",
                    "type":"eissn"
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
                "title":"Janeway JS",
                "number":"1",
                "language":[
                    "en"
                ]
            },
            "keywords":[

            ],
            "year":2019,
            "month":7,
            "title":"The art of writing test titles",
            "link":[
                {
                    "url":"http://www.example.com/doaj/article/id/1/",
                    "content_type":"text/html",
                    "type":"fulltext"
                }
            ],
            "abstract":"The test abstract"
            }
        }
        """

    def _create_article(self, **kwargs):
        kwargs.setdefault("abstract", "The test abstract")
        kwargs.setdefault("title", "The art of writing test titles")
        kwargs.setdefault("date_published", timezone.now())
        kwargs.setdefault("journal", self.journal)
        article = Article(**kwargs)
        article.save()

        author = create_user("author@doaj.com")
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
        print(doaj_article.link)

        self.assertEqual(article.title, doaj_article.title)

    @override_settings(DOAJ_API_TOKEN="dummy_key")
    def test_encode_article(self):
        doaj_article = DOAJArticle.from_article_model(self.article)
        result = doaj_article.encode()
        import json;print(json.loads(self.encoded_article))
        self.maxDiff = None
        print(json.loads(result))
        raise Exception
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

