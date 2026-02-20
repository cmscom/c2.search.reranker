"""Shared search-and-rerank logic for integrating with Plone's default search.

This module provides the core function ``search_and_rerank`` that can be used
by both the REST API ``@search`` service and the classic ``@@search`` view.
It optionally combines keyword search with vector search (hybrid mode) and
applies content-type boost and time-decay reranking.
"""

from c2.search.reranker import logger
from c2.search.reranker.interfaces import IRerankerSettings
from c2.search.reranker.reranker import (
    RerankerSettings,
    calculate_time_decay,
    get_content_age_days,
    rerank_brains,
)
from DateTime import DateTime
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from zope.component import getUtility

# RRF constant: prevents top-ranked items from dominating too much.
RRF_K = 60


def is_reranker_enabled():
    """Check whether the reranker is enabled in the control panel."""
    try:
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IRerankerSettings)
        return settings.reranker_enabled
    except Exception:
        logger.debug("Could not read reranker_enabled setting, defaulting to False")
        return False


def is_vectorsearch_available():
    """Check if collective.vectorsearch is importable."""
    try:
        from collective.vectorsearch.vector_index import VectorIndex  # noqa: F401

        return True
    except ImportError:
        return False


def find_vector_index(catalog):
    """Find the first VectorIndex in catalog, or None."""
    for idx_name in catalog.Indexes:
        idx = catalog.Indexes[idx_name]
        if getattr(idx, "meta_type", "") == "VectorIndex":
            return idx
    return None


def keyword_search(catalog, search_text, query_extras=None):
    """Execute keyword search via catalog.

    Returns dict: {rid: (brain, normalized_score)}
    """
    query = {"SearchableText": search_text, "sort_limit": 200}
    if query_extras:
        query.update(query_extras)
    brains = list(catalog.searchResults(**query))
    result = {}
    max_score = 0.0
    for brain in brains:
        rid = brain.getRID()
        score = getattr(brain, "data_record_normalized_score_", None)
        score = 1.0 if score is None or score == 0 else float(score)
        if score > max_score:
            max_score = score
        result[rid] = (brain, score)

    # Normalize to 0.0-1.0 range
    if max_score > 0:
        result = {
            rid: (brain, score / max_score) for rid, (brain, score) in result.items()
        }
    return result


def vector_search(vector_index, search_text):
    """Execute vector search via VectorIndex.

    Returns dict: {rid: vector_score_normalized}
    """

    class QueryRecord:
        def __init__(self, text):
            self.keys = [text]

    record = QueryRecord(search_text)
    bucket = vector_index.query_index(record)

    if bucket is None:
        return {}

    result = {}
    for rid, int_score in bucket.items():
        result[rid] = float(int_score) / 100_000_000.0
    return result


def get_brain_by_rid(catalog, rid):
    """Get a catalog brain for a given RID."""
    try:
        path = catalog.getpath(rid)
        results = catalog.searchResults(path={"query": path, "depth": 0})
        if results:
            return results[0]
    except Exception:
        logger.debug("Could not resolve brain for RID %s", rid)
    return None


def compute_rrf_scores(keyword_results, vector_results):
    """Compute RRF (Reciprocal Rank Fusion) scores from rank positions.

    Returns (kw_rrf, vec_rrf) dicts mapping rid to RRF score.
    """
    k = RRF_K

    kw_ranked = sorted(
        keyword_results.keys(),
        key=lambda rid: keyword_results[rid][1],
        reverse=True,
    )
    kw_rrf = {}
    for rank, rid in enumerate(kw_ranked, start=1):
        kw_rrf[rid] = 1.0 / (k + rank)

    vec_ranked = sorted(
        vector_results.keys(),
        key=lambda rid: vector_results[rid],
        reverse=True,
    )
    vec_rrf = {}
    for rank, rid in enumerate(vec_ranked, start=1):
        vec_rrf[rid] = 1.0 / (k + rank)

    return kw_rrf, vec_rrf


def get_vector_index(catalog, settings):
    """Get the vector index if vector search is available and enabled.

    Returns the VectorIndex object, or None.
    """
    if not settings.vector_search_enabled:
        return None
    if not is_vectorsearch_available():
        return None
    return find_vector_index(catalog)


def search_and_rerank(context, search_text, query_extras=None):
    """Execute search with reranking, optionally with hybrid vector search.

    When vector_search_enabled is True and collective.vectorsearch is available:
      - Combines keyword + vector search using RRF or weighted scoring
      - Applies content-type boost and time-decay

    When vector_search_enabled is False (or vector search unavailable):
      - Executes keyword search only
      - Applies content-type boost and time-decay via rerank_brains()

    Args:
        context: Plone context (for catalog access)
        search_text: SearchableText query string
        query_extras: additional catalog query params (path, portal_type, etc.)
            Note: sort_on/sort_order/sort_limit/b_start/b_size should be
            excluded since reranking produces its own ordering.

    Returns:
        list of catalog brains in reranked order
    """
    catalog = getToolByName(context, "portal_catalog")
    registry = getUtility(IRegistry)
    settings = registry.forInterface(IRerankerSettings)

    vector_index = get_vector_index(catalog, settings)

    if vector_index is not None:
        return _hybrid_search_and_rerank(
            catalog,
            search_text,
            vector_index,
            settings.keyword_search_ratio,
            settings.scoring_mode,
            query_extras,
        )

    # Keyword-only mode: use simple rerank_brains
    return _keyword_search_and_rerank(catalog, search_text, query_extras)


def _keyword_search_and_rerank(catalog, search_text, query_extras=None):
    """Keyword search only, reranked with boost and decay."""
    query = {"SearchableText": search_text, "sort_limit": 200}
    if query_extras:
        query.update(query_extras)
    brains = list(catalog.searchResults(**query))
    if not brains:
        return []
    ranked = rerank_brains(brains)
    return [brain for brain, _score_details in ranked]


def _hybrid_search_and_rerank(
    catalog,
    search_text,
    vector_index,
    keyword_ratio,
    scoring_mode,
    query_extras=None,
):
    """Hybrid keyword + vector search, with boost and decay."""
    now = DateTime()
    reranker_settings = RerankerSettings()

    # Step 1: Keyword search
    keyword_results = keyword_search(catalog, search_text, query_extras)

    # Step 2: Vector search
    try:
        vector_results = vector_search(vector_index, search_text)
    except Exception as e:
        logger.warning("Vector search failed, falling back to keyword only: %s", e)
        vector_results = {}
        keyword_ratio = 100

    if not vector_results:
        keyword_ratio = 100

    # Step 3: Combine scores
    kw = keyword_ratio / 100.0
    vw = 1.0 - kw
    use_rrf = scoring_mode == "rrf"

    kw_rrf = {}
    vec_rrf = {}
    if use_rrf and vector_results:
        kw_rrf, vec_rrf = compute_rrf_scores(keyword_results, vector_results)

    all_rids = set(keyword_results.keys()) | set(vector_results.keys())
    scored = []

    for rid in all_rids:
        kw_data = keyword_results.get(rid)
        vs = vector_results.get(rid, 0.0)

        if kw_data is not None:
            brain, ks = kw_data
        else:
            ks = 0.0
            brain = get_brain_by_rid(catalog, rid)
            if brain is None:
                continue

        if use_rrf and vector_results:
            kr = kw_rrf.get(rid, 0.0)
            vr = vec_rrf.get(rid, 0.0)
            combined = kr * kw + vr * vw
        else:
            combined = ks * kw + vs * vw

        # Step 4: Apply boost and decay
        portal_type = brain.portal_type
        boost = reranker_settings.get_boost(portal_type)
        halflife = reranker_settings.get_halflife(portal_type)
        age_days = get_content_age_days(brain, now=now)
        decay = calculate_time_decay(age_days, halflife)

        final_score = combined * boost * decay
        scored.append((brain, final_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [brain for brain, _score in scored]
