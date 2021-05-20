class InvalidDOAJToken(Exception):
    pass

class MultipleResultsFound(Exception):
    pass

class ResultNotFound(Exception):
    pass

class RequestFailed(Exception):
    pass

class ImmutableFieldChanged(Exception):
    """ A parameter has changed and DOAJ rejects write requests for the object

    While it is not documented, we've seen this happening when attempting to
    update the URL or identifier for an article.
    """
    pass

class BadRequest(Exception):
    pass
