class BaseStruct():
    __slots__ = []
    def __init__(self, *args, **kwargs):
        if args:
            for value, slot in zip(args, self.__slots__):
                setattr(self, slot, value)
        if kwargs:
            for key, value in kwargs.items():
                setattr(self, key, value)

    def __eq__(self, other):
        try:
            return all(
                getattr(self, field, None) == getattr(other, field, None)
                for field in self.__slots__
            )
        except AttributeError:
            raise TypeError(
                "Can't compare objects of tupe {} and {}"
                "".format(self.__class__.__name__, other.__class__.__name__)
            )

    def __repr__(self):
        kwargs = []
        for slot in self.__slots__:
            try:
                val = getattr(self, slot)
            except AttributeError:
                val = None
            kwargs.append("{}={}".format(slot, val))
        return "{}{}".format(self.__class__.__name__, tuple(kwargs))

    def __str__(self):
        return repr(self)




class AuthorStruct(BaseStruct):
    __slots__ = ["name", "affiliation"]


class IdentifierStruct(BaseStruct):
    __slots__ = ["type", "id"]


class JournalStruct(BaseStruct):
    __slots__ =  [
        "language", "license", "number",
        "title", "volume", "publisher",
        "start_page", "end_page", "country",
        "issns",
    ]


class LinkStruct(BaseStruct):
    __slots__ = ["content_type", "type", "url"]


class LicenseStruct(BaseStruct):
    __slots__ = ["open_access", "title", "url", "type"]


class AdminStruct(BaseStruct):
    __slots__ = ["in_doaj", "publisher_record_id", "upload_id", "seal"]


class SubjectStruct(BaseStruct):
    __slots__ = ["code", "scheme", "term"]


class BibjsonStruct(BaseStruct):
    __slots__ = [
        "abstract", "title", "year", "month",
        "identifier", "journal", "keywords",
        "link", "author", "subject", "start_page",
        "end_page",
]
    @property
    def doi(self):
        if self.identifier:
            for i in self.identifier:
                if i.type == "doi":
                    return i.id
        return None


class ArticleSearchResultStruct(BaseStruct):
    __slots__ = ["admin", "bibjson", "id", "created_date", "last_updated"]

    @property
    def doi(self):
        if self.bibjson:
            return self.bibjson.doi


class SearchResultStruct(BaseStruct):
    __slots__ = ["id", "last_updated", "created_date"]
