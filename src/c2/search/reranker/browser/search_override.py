"""Override Plone's classic @@search and @@ajax-search with reranking."""

import os

from c2.search.reranker import _
from c2.search.reranker.search import is_reranker_enabled
from c2.search.reranker.search import search_and_rerank
from plone.app.contentlisting.interfaces import IContentListing
from plone.base.batch import Batch
from Products.CMFPlone.browser.search import AjaxSearch
from Products.CMFPlone.browser.search import Search
from Products.CMFPlone.browser.search import SortOption
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.ZCTextIndex.ParseTree import ParseError
from zope.i18nmessageid import MessageFactory

import Products.CMFPlone.browser

_plone = MessageFactory("plone")

_SEARCH_TEMPLATE = os.path.join(
    os.path.dirname(Products.CMFPlone.browser.__file__),
    "templates",
    "search.pt",
)

# Sort key used for our custom reranker algorithm
RERANKER_SORT_KEY = "reranker"


class RerankedSearch(Search):
    """Search view that applies reranking when enabled."""

    index = ViewPageTemplateFile(_SEARCH_TEMPLATE)

    def __call__(self):
        return self.index()

    def sort_options(self):
        """Add 'custom algorithm' sort option when reranker is enabled."""
        if not is_reranker_enabled():
            return super().sort_options()

        if "sort_on" not in self.request.form:
            self.request.form["sort_on"] = RERANKER_SORT_KEY
        return (
            SortOption(
                self.request,
                _(
                    "label_sort_reranker",
                    default="custom algorithm",
                ),
                RERANKER_SORT_KEY,
            ),
            SortOption(self.request, _plone("relevance"), "relevance"),
            SortOption(
                self.request,
                _plone("date (newest first)"),
                "Date",
                reverse=True,
            ),
            SortOption(self.request, _plone("alphabetically"), "sortable_title"),
        )

    def filter_query(self, query):
        """Handle 'reranker' sort key before parent processing."""
        form_sort = self.request.form.get("sort_on", "")
        is_reranker_sort = form_sort == RERANKER_SORT_KEY

        if is_reranker_sort:
            # Temporarily set to "relevance" so parent doesn't pass
            # unknown sort key to the catalog
            self.request.form["sort_on"] = "relevance"

        result = super().filter_query(query)

        if is_reranker_sort:
            self.request.form["sort_on"] = RERANKER_SORT_KEY

        return result

    def results(
        self,
        query=None,
        batch=True,
        b_size=10,
        b_start=0,
        use_content_listing=True,
    ):
        if not is_reranker_enabled():
            return super().results(
                query=query,
                batch=batch,
                b_size=b_size,
                b_start=b_start,
                use_content_listing=use_content_listing,
            )

        # Only apply reranking when "reranker" sort is active
        sort_on = self.request.form.get("sort_on", "")
        if sort_on and sort_on != RERANKER_SORT_KEY:
            return super().results(
                query=query,
                batch=batch,
                b_size=b_size,
                b_start=b_start,
                use_content_listing=use_content_listing,
            )

        return self._reranked_results(
            query=query,
            batch=batch,
            b_size=b_size,
            b_start=b_start,
            use_content_listing=use_content_listing,
        )

    def _reranked_results(
        self,
        query=None,
        batch=True,
        b_size=10,
        b_start=0,
        use_content_listing=True,
    ):
        """Execute search with reranking algorithm."""
        if query is None:
            query = {}
        if batch:
            b_start = int(b_start)
        query = self.filter_query(query)

        if query is None:
            results = []
        else:
            search_text = query.get("SearchableText")
            if not search_text:
                # No text search: reranking is not meaningful,
                # fall back to normal catalog search
                catalog = getToolByName(self.context, "portal_catalog")
                try:
                    results = catalog(**query)
                except ParseError:
                    return []
            else:
                # Build query extras (excluding search text and sort/batch params)
                query_extras = {
                    k: v
                    for k, v in query.items()
                    if k
                    not in (
                        "SearchableText",
                        "sort_on",
                        "sort_order",
                        "sort_limit",
                        "b_start",
                        "b_size",
                    )
                }
                try:
                    results = search_and_rerank(
                        self.context,
                        search_text,
                        query_extras or None,
                    )
                except ParseError:
                    return []

        if use_content_listing:
            results = IContentListing(results)
        if batch:
            results = Batch(results, b_size, b_start)
        return results


class RerankedAjaxSearch(RerankedSearch, AjaxSearch):
    """Ajax search view that uses reranked results.

    Inherits results() from RerankedSearch and __call__ from AjaxSearch.
    """

    pass
