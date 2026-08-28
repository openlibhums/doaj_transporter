import datetime
import json
from unittest import mock

from core import models as core_models
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from identifiers import models as id_models
from journal.models import Journal, Issue
from press.models import Press
from submission.models import Article, FrozenAuthor, Licence
from submission.models import FrozenAuthor
from utils.testing import helpers
from utils import install

from plugins.doaj_transporter import exceptions
from plugins.doaj_transporter import models as doaj_models
from plugins.doaj_transporter.clients import DOAJArticle, ArticleSearchClient

SETTINGS_PATH = "plugins/doaj_transporter/install/settings.json"

BAD_REQUEST_BODY = (
    '{"status": "bad_request", "error": "bibjson.keywords may only contain '
    'a maximum of 6 keywords (ref: 383e725e-bcb4-11eb-91b5-6ac132d54a90)"}'
)


class MockResponse(mock.Mock):
    def __init__(self, content=None, ok=True, status_code=200,
                 url="https://doaj.org/api/v2/articles", **kwargs):
        super().__init__(**kwargs)
        self.content = content or ""
        self._ok = ok
        self.status_code = status_code
        self.request = mock.Mock(url=url)

    @property
    def text(self):
        return self.content

    @property
    def ok(self):
        return self._ok

    def json(self):
        return json.loads(self.content)


class TestDOAJArticleClient(TestCase):
    def setUp(self):
        press = helpers.create_press()
        self.journal, _ = helpers.create_journals()
        self.journal.save()
        call_command('load_default_settings')
        helpers.create_roles(["author"])
        self.journal.publisher = "doaj"
        self.journal.code = "doaj"
        self.journal.save()

        install.update_settings(
            self.journal, file_path=SETTINGS_PATH)

        self.article = self._create_article(
            date_published=datetime.date(day=1, month=7,year=2019))
        self.encoded_article = """
        {
        "admin": {
            "publisher_record_id": null
        },
        "bibjson":{
        "end_page": null,
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
                    "affiliation":"OLH",
                    "orcid_id": "https://orcid.org/0000-0000-0000-0000"
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
            "year": "2019",
            "month": "7",
            "start_page": null,
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
        author.orcid = "0000-0000-0000-0000"
        author.first_name = "Testla"
        author.last_name = "Musketeer"
        author.institution = "OLH"
        author.save()
        author.snapshot_self(article=article)
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

    def test_insert_article(self):
        doaj_article = DOAJArticle.from_article_model(self.article)
        with mock.patch.object(
            doaj_article, "_post", return_value=None) as caller:
            doaj_article.upsert()

            caller.assert_called_with("api_key=", article_id='')

    def test_update_article(self):
        id_models.Identifier.objects.create(
            article=self.article,
            id_type="doaj",
            identifier="test",
        )
        doaj_article = DOAJArticle.from_article_model(self.article)
        with mock.patch.object(
            doaj_article, "_put", return_value=None) as caller:
            doaj_article.upsert()

            caller.assert_called_with("api_key=", article_id='test')

    def test_delete_article(self):
        id_models.Identifier.objects.create(
            article=self.article,
            id_type="doaj",
            identifier="test",
        )
        doaj_article = DOAJArticle.from_article_model(self.article)
        with mock.patch.object(
            doaj_article, "_delete", return_value=None) as caller:
            doaj_article.delete()

            caller.assert_called_with("api_key=", article_id='test')
        self.assertEqual(doaj_article.id, None)
        with self.assertRaises(id_models.Identifier.DoesNotExist):
            id_models.Identifier.objects.get(
                article=self.article,
                id_type="doaj",
                identifier="test",
            )

    def test_insert_article_bad_request_is_logged(self):
        doaj_article = DOAJArticle.from_article_model(self.article)
        mock_session = mock.MagicMock()
        mock_session.post.return_value = MockResponse(
            BAD_REQUEST_BODY, ok=False, status_code=400)
        with mock.patch(
            "plugins.doaj_transporter.clients.session",
            return_value=mock_session,
        ):
            with self.assertRaises(exceptions.BadRequest):
                doaj_article.upsert()

        deposit = doaj_models.DOAJDeposit.objects.get(article=self.article)
        self.assertFalse(deposit.success)
        self.assertEqual(deposit.result_text, BAD_REQUEST_BODY)

    def test_update_article_bad_request_is_logged(self):
        id_models.Identifier.objects.create(
            article=self.article,
            id_type="doaj",
            identifier="test",
        )
        doaj_article = DOAJArticle.from_article_model(self.article)
        mock_session = mock.MagicMock()
        mock_session.put.return_value = MockResponse(
            BAD_REQUEST_BODY, ok=False, status_code=400)
        with mock.patch(
            "plugins.doaj_transporter.clients.session",
            return_value=mock_session,
        ):
            with self.assertRaises(exceptions.BadRequest):
                doaj_article.upsert()

        deposit = doaj_models.DOAJDeposit.objects.get(article=self.article)
        self.assertFalse(deposit.success)
        self.assertEqual(deposit.identifier, "test")
        self.assertEqual(deposit.result_text, BAD_REQUEST_BODY)

    def test_upsert_sends_content_type_header(self):
        doaj_article = DOAJArticle.from_article_model(self.article)
        mock_session = mock.MagicMock()
        mock_session.post.return_value = MockResponse(
            BAD_REQUEST_BODY, ok=False, status_code=400)
        with mock.patch(
            "plugins.doaj_transporter.clients.session",
            return_value=mock_session,
        ):
            with self.assertRaises(exceptions.BadRequest):
                doaj_article.upsert()

        _, kwargs = mock_session.post.call_args
        self.assertEqual(
            kwargs["headers"], {"Content-type": "application/json"})

    def test_bad_request_without_janeway_article(self):
        # Clients built from a DOAJ id have no article to log against
        mock_session = mock.MagicMock()
        mock_session.get.return_value = MockResponse(
            BAD_REQUEST_BODY, ok=False, status_code=400)
        with mock.patch(
            "plugins.doaj_transporter.clients.session",
            return_value=mock_session,
        ):
            with self.assertRaises(exceptions.BadRequest):
                DOAJArticle.from_doaj_id("test", "dummy_key")

        self.assertFalse(doaj_models.DOAJDeposit.objects.exists())

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
        with mock.patch("doaj_transporter.clients.requests", mock_requests):
            client = ArticleSearchClient()
            client.search("10.001/mock.01")
            self.assertTrue(client.one().in_doaj)

