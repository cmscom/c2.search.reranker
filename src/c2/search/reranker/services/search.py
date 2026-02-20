"""Custom @search GET service that optionally applies reranking."""

from c2.search.reranker.search import is_reranker_enabled
from c2.search.reranker.search import search_and_rerank
from plone.restapi.batching import HypermediaBatch
from plone.restapi.interfaces import ISerializeToJson
from plone.restapi.interfaces import ISerializeToJsonSummary
from plone.restapi.search.handler import SearchHandler
from plone.restapi.search.utils import unflatten_dotted_dict
from plone.restapi.services import Service
from zope.component import getMultiAdapter

import logging


log = logging.getLogger(__name__)

# Keys to exclude from query_extras when building reranker query
_SORT_AND_BATCH_KEYS = frozenset((
    "SearchableText",
    "sort_on",
    "sort_order",
    "sort_limit",
    "b_start",
    "b_size",
))


class RerankerSearchGet(Service):
    """Custom @search GET service that optionally applies reranking.

    When reranker_enabled is True in the control panel settings,
    this service intercepts the catalog results, applies the
    reranking algorithm (content-type boost + time-decay, and
    optionally hybrid vector search), and returns the reranked
    results with proper batching.

    When reranker_enabled is False, this delegates entirely to the
    default SearchHandler with zero overhead.
    """

    def reply(self):
        query = self.request.form.copy()
        query = unflatten_dotted_dict(query)

        if not is_reranker_enabled():
            return SearchHandler(self.context, self.request).search(query)

        return self._search_with_reranking(query)

    def _prepare_query(self, query):
        """Parse and prepare the query, extracting flags.

        Returns (query, fullobjects) tuple.
        """
        handler = SearchHandler(self.context, self.request)

        fullobjects = query.pop("fullobjects", None) is not None
        use_site_search_settings = (
            query.pop(
                "use_site_search_settings",
                None,
            )
            is not None
        )

        if use_site_search_settings:
            query = handler.filter_query(query)

        if "SearchableText" in query:
            # quote_chars may not exist in older plone.restapi (Plone 5.2)
            quote_fn = getattr(handler, "quote_chars", None)
            if quote_fn:
                query["SearchableText"] = quote_fn(query["SearchableText"])
            if not query["SearchableText"] or query["SearchableText"] == "*":
                return None, fullobjects

        # These private methods may not exist in older plone.restapi
        constrain_fn = getattr(handler, "_constrain_query_by_path", None)
        if constrain_fn:
            constrain_fn(query)
        parse_fn = getattr(handler, "_parse_query", None)
        if parse_fn:
            query = parse_fn(query)
        return query, fullobjects

    def _search_with_reranking(self, query):
        """Execute search, apply reranking, and return batched JSON results."""
        query, fullobjects = self._prepare_query(query)
        if query is None:
            return []

        search_text = query.get("SearchableText")
        if not search_text:
            # No text search: delegate to normal serialization
            handler = SearchHandler(self.context, self.request)
            lazy_resultset = handler.catalog.searchResults(**query)
            return getMultiAdapter((lazy_resultset, self.request), ISerializeToJson)(
                fullobjects=fullobjects
            )

        query_extras = {k: v for k, v in query.items() if k not in _SORT_AND_BATCH_KEYS}

        reranked_brains = search_and_rerank(
            self.context,
            search_text,
            query_extras or None,
        )

        return self._serialize_results(reranked_brains, fullobjects)

    def _serialize_results(self, brains, fullobjects=False):
        """Serialize a list of brains with batching."""
        batch = HypermediaBatch(self.request, brains)

        results = {
            "@id": batch.canonical_url,
            "items_total": batch.items_total,
        }
        links = batch.links
        if links:
            results["batching"] = links

        results["items"] = []
        for brain in batch:
            if fullobjects:
                try:
                    obj = brain.getObject()
                except KeyError:
                    log.warning(
                        "Brain getObject error: %s doesn't exist anymore",
                        brain.getPath(),
                    )
                    continue
                result = getMultiAdapter((obj, self.request), ISerializeToJson)(
                    include_items=False
                )
            else:
                result = getMultiAdapter(
                    (brain, self.request), ISerializeToJsonSummary
                )()
            results["items"].append(result)

        return results
