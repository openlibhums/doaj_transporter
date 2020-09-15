from collections import namedtuple
import time

from django.conf import settings
from django.utils.html import strip_tags
from django.utils.http import urlencode
from identifiers.models import DOI_RE
import requests
from utils.logger import get_logger

from doaj_transporter.data_structs import(
    AdminStruct,
    AuthorStruct,
    BaseStruct,
    BibjsonStruct,
    IdentifierStruct,
    JournalStruct,
    LicenseStruct,
    LinkStruct,
)
from doaj_transporter import exceptions
from doaj_transporter import plugin_settings
from doaj_transporter import schemas


logger = get_logger(__name__)

JOURNAL_SLOTS = (
        # Admin
        "application_status", "contact", "current_journal", "owner",
        # Bibjson
        "allows_full_text_indexing", "alternative_title","license", "link",
        "keywords", "language", "identifier", "article_statistics",
        "plagiarism_detection", "provider", "publisher", "subject",
        "title",
        # Record Metadata

        "created_date", "id", "last_updated"
)

class BaseDOAJClient(object):
    """ A base client for CRUD operations via the DOAJ API"""
    API_URL = "https://doaj.org/api/v1{operation}"
    OP_PATH = ""
    SCHEMA = None
    VERBS = set()

    def __init__(self, api_token, codec=None, *args, **kwargs):
        self.api_token = api_token
        self._codec = codec or self.SCHEMA()
        super().__init__(*args, **kwargs)

    def __iter__(self):
        for field in self.__slots__:
            yield getattr(self, field, None)

    def __eq__(self, other):
        return all(
            this_val == other_val
            for this_val, other_val in zip(self, other)
        )
    def __repr__(self):
        kwargs = tuple(
            "{}={}".format(slot,val) for slot, val in zip(self.__slots__, self)
        )
        return "{}{}".format(self.__class__.__name__, kwargs)

    def __str__(self):
        return repr(self)

    def _get(self, querystring=None, **path_vars):
        if "GET" in self.VERBS:
            url = self._build_url(querystring, **path_vars)
            return self._fetch(url, requests.get)
        else:
            raise NotImplementedError("%s does not support GET requests")

    def _put(self, querystring=None, headers=None, **path_vars):
        if "PUT" in self.VERBS:
            url = self._build_url(querystring, **path_vars)
            if headers is None:
                headers = {}
            headers = {'Content-type': 'application/json'}.update(headers)
            return self._fetch(requests.put, body=self.encode, headers=headers)
        else:
            raise NotImplementedError("%s does not support PUT requests")

    def _post(self, querystring=None, headers=None, **path_vars):
        if "POST" in self.VERBS:
            url = self._build_url(querystring, **path_vars)
            if headers is None:
                headers = {}
            headers = {'Content-type': 'application/json'}.update(headers)
            return self._fetch(requests.put, body=self.encode, headers=headers)
        else:
            raise NotImplementedError("%s does not support POST requests")

    def _delete(self):
        raise NotImplementedError("%s does not support DELETE requests")

    def _fetch(self, url, method, body=None, headers=None):
        response = method(url)
        if self._validate_response(response):
            if settings.DEBUG:
                logger.debug(response.text)
            self._decode(response.text)

    def _build_url(self, querystring, **path_args):
        url = self.API_URL.format(operation=self.OP_PATH.format(**path_args))
        if querystring:
            url += "?%s" % querystring
        return url

    def encode(self):
        return self._codec.dumps(self)

    def _decode(self, encoded):
        decoded = self._codec.loads(encoded)
        for key, value in decoded.items():
            setattr(self, key, value)

    def _validate_response(self, response):
        """ Validates the status code of the response

        If the status code is not success (2[x][x]) it raises
        an HttpError
        :param response: An HttpResponse
        :returns bool: True
        """
        # Check for 2xx status code
        if response.ok:
            return True
        else:
            response.raise_for_status()


class DOAJArticle(BaseDOAJClient):
    OP_PATH = "/articles/{article_id}"
    SCHEMA = schemas.ArticleSchema
    VERBS = {"GET", "POST", "PUT"}

    __slots__ = [
        # Admin
        "in_doaj", "publisher_record_id", "upload_id", "seal",
        # Bibjson
        "abstract", "title", "year", "month", "author", "journal",
        "keywords", "link", "persistent_identifier_scheme", "subject",
        # Record Metadata
        "created_date", "id", "last_updated"
    ]

    @property
    def admin(self):
        return AdminStruct(
            *(getattr(self, field, None) for field in AdminStruct.__slots__))

    @property
    def bibjson(self):
        return BibjsonStruct(
            *(getattr(self, field, None) for field in BibjsonStruct.__slots__))

    @admin.setter
    def admin(self, admin_struct):
        for field in admin_struct.__slots__:
            setattr(self, field, getattr(admin_struct, field, None))

    @bibjson.setter
    def bibjson(self, bibjson_struct):
        for field in bibjson_struct.__slots__:
            setattr(self, field, getattr(bibjson_struct, field, None))

    @classmethod
    def from_article_model(cls, article):
        token = plugin_settings.DOAJ_API_TOKEN
        doaj_article = cls(token)
        doaj_article.abstract = strip_tags(article.abstract)
        doaj_article.title = strip_tags(article.title)
        doaj_article.year = int(article.date_published.year)
        doaj_article.month = int(article.date_published.month)
        doaj_article.author = [
            cls.transform_author(a) for a in article.authors.all()]
        doaj_article.journal = cls.transform_journal(article)
        doaj_article.keywords = [kw.word for kw in article.keywords.all()]
        doaj_article.link = cls.transform_urls(article)
        doaj_article.identifier = cls.transform_identifiers(article)

        return doaj_article

    @classmethod
    def from_doaj_id(cls, doaj_id):
        token = plugin_settings.DOAJ_API_TOKEN
        doaj_article = cls(token)
        doaj_article.id = doaj_id
        doaj_article.load()
        return doaj_article

    def load(self):
        querystring = urlencode({"api_key": self.api_token})
        self._get(querystring, article_id=self.id)

    def create(self):
        pass

    @staticmethod
    def transform_author(author):
        return AuthorStruct(
            name=author.full_name(),
            affiliation=author.affiliation(),
        )

    @staticmethod
    def transform_urls(article):
        links = []
        if article.url:
            links.append(LinkStruct(
                content_type="text/html",
                type="fulltext",
                url=article.url,
            ))
        if article.pdfs:
            links.append(LinkStruct(
                content_type="application/pdf",
                type="fulltext",
                url=article.pdf_url,
            ))

        return links

    @classmethod
    def transform_journal(cls, article):
        return JournalStruct(
            language=[settings.LANGUAGE_CODE],
            license=cls.transform_license(article),
            number=str(article.issue.issue) if article.issue else None,
            volume=str(article.issue.volume) if article.issue else None,
            title=article.journal.name,
            publisher=article.journal.publisher,
        )

    @staticmethod
    def transform_license(article):
        license = []
        if article.license:
            license.append(LicenseStruct(
                open_access=True,
                title=article.license.name,
                url=article.license.url
            ))
        return license

    @staticmethod
    def transform_identifiers(article):
        identifiers = []
        identifiers.append(
            IdentifierStruct(
                type="eissn",
                id=article.journal.issn,
            )
        )
        if article.get_doi:
            identifiers.append(
                IdentifierStruct(
                    type="doi",
                    id=article.get_doi(),
                )
            )
        return identifiers


class BaseSearchClient(BaseDOAJClient):
    OP_PATH = "/search/{search_type}/{search_query}"
    SEARCH_TYPE = ""
    SEARCH_QUERY_PREFIX = ""
    SCHEMA = schemas.SearchSchema
    VERBS= {"GET"}
    THROTTLE_SECS = 0.250
    PAGE_SIZE = 50

    __slots__ = ["results", "next", "previous", "last"]

    def search(self, search_term, prefix=None):
        if prefix:
            search_query = "%s:%s" % (prefix, search_term)
        elif self.SEARCH_QUERY_PREFIX:
            search_query = "%s:%s" % (self.SEARCH_QUERY_PREFIX, search_term)
        else:
            search_query = search_term
        querystring = urlencode(
            {"api_key": self.api_token, "pageSize":self.PAGE_SIZE})
        self._get(
            querystring=querystring,
            search_query=search_query,
            search_type=self.SEARCH_TYPE,
        )
        return iter(self)

    def _turn_page(self):
        if hasattr(self, "next") and self.total / self.page >= self.pageSize:
            logger.debug("Thread sleeping for %ss" % self.THROTTLE_SECS)
            time.sleep(self.THROTTLE_SECS)
            self._fetch(self.next, requests.get)
            return True
        else:
            return False

    def __iter__(self):
        for result in self.results:
            yield result
        # Chain results from next pages
        turned = self._turn_page()
        if turned:
            for result in self:
                yield result

    def __repr__(self):
        try:
            return "{}({})".format(
                self.__class__.__name__,
                "total={},page={},pageSize={}".format(
                    self.total, self.page, self.pageSize),
            )
        except AttributeError:
            return "{}()".format(self.__class__.__name__)


class ApplicationSearchClient(BaseSearchClient):
    SEARCH_TYPE = "applications"
    SEARCH_QUERY_PREFIX = "issn"


class ArticleSearchClient(BaseSearchClient):
    """ Can search articles by DOI"""
    SEARCH_TYPE = "articles"
    SCHEMA = schemas.ArticleSearchSchema

    def one(self):
        if len(self.results) > 1:
            raise exceptions.MultipleResultsFound(
                "Found %d!" % len(self.results))
        elif len(self.results) < 1:
            raise exceptions.ResultNotFound(
                "Search returned zero results")
        else:
            return self.results[0]

    def search_by_doi(self, doi, exact=False):
        match = DOI_RE.match(doi)
        if not match:
            raise ValueError("%s is not a valid doi" % doi)
        if exact:
            prefix="doi.exact"
        else:
            prefix="doi"
        return self.search(match, prefix=prefix)

    def search_by_publisher(self, publisher, exact=False):
        if exact:
            prefix="publisher.exact"
        else:
            prefix="publisher"
        return self.search(publisher, prefix=prefix)


class ApplicationClient(BaseDOAJClient):
    OP_PATH = "/applications/{application_id}"
#    SCHEMA = schemas.ApplicationSchema

    __slots__ = JOURNAL_SLOTS


class ArticleBulkClient(BaseDOAJClient):
    OP_PATH = "/bulk/articles"

    def delete(self):
        pass

    def update(self):
        pass
