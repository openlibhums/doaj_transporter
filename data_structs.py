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
        return all(
            getattr(self, field, None) == getattr(other, field, None)
            for field in self.__slots__
        )


class AuthorStruct(BaseStruct):
    __slots__ = ["name", "affiliation"]


class IdentifierStruct(BaseStruct):
    __slots__ = ["type", "id"]


class JournalStruct(BaseStruct):
    __slots__ =  [
        "language", "license", "number",
        "title", "volume", "publisher",
        "start_page", "end_page", "country",
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
        "link", "author", "subject",
]


class SearchResultStruct(BaseStruct):
    __slots__ = ["id", "last_updated", "created_date"]
