# inventory/pagination.py
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Default API pagination: 25 per page, client may request up to 100."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class DefinitionsResultsSetPagination(StandardResultsSetPagination):
    """
    List pagination for definition resources:
    authors, customers, translators, rights owners, warehouses.
    Same limits as StandardResultsSetPagination — explicit for clarity.
    """

    pass
