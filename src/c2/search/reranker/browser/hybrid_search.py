"""Browser view for hybrid search combining keyword and vector search."""

from c2.search.reranker import logger
from c2.search.reranker.interfaces import IRerankerSettings
from c2.search.reranker.reranker import (
    RerankerSettings,
    calculate_time_decay,
    get_content_age_days,
)
from DateTime import DateTime
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from zope.component import getUtility


class HybridSearchView(BrowserView):
    """Browser view that displays hybrid search results with score details.

    Combines keyword search (ZCTextIndex) with vector search
    (collective.vectorsearch) using weighted scoring.

    Access via: @@hybrid-search?SearchableText=keyword
    """

    # RRF constant: prevents top-ranked items from dominating too much.
    RRF_K = 60

    def __call__(self):
        self.search_text = self.request.form.get("SearchableText", "")
        self.results = []
        self.error = ""
        self.vector_message = ""
        self.vector_index_name = None

        registry = getUtility(IRegistry)
        settings = registry.forInterface(IRerankerSettings)
        self.vector_enabled = settings.vector_search_enabled
        self.keyword_ratio = settings.keyword_search_ratio
        # URL parameter overrides registry default (for test page)
        self.scoring_mode = self.request.form.get("scoring_mode", settings.scoring_mode)
        self.effective_keyword_ratio = self.keyword_ratio
        self.effective_vector_ratio = 100 - self.keyword_ratio

        if self.search_text:
            try:
                self.results = self._search_hybrid()
            except Exception as e:
                self.error = str(e)

        return self.index()

    def _is_vectorsearch_available(self):
        """Check if collective.vectorsearch is importable."""
        try:
            from collective.vectorsearch.vector_index import VectorIndex  # noqa: F401

            return True
        except ImportError:
            return False

    def _find_vector_index(self, catalog):
        """Find the first VectorIndex in catalog.

        Returns the index object or None.
        """
        for idx_name in catalog.Indexes:
            idx = catalog.Indexes[idx_name]
            if getattr(idx, "meta_type", "") == "VectorIndex":
                return idx
        return None

    def _keyword_search(self, catalog):
        """Execute keyword search via catalog.

        Returns dict: {rid: (brain, normalized_score)}
        """
        query = {"SearchableText": self.search_text, "sort_limit": 200}
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
                rid: (brain, score / max_score)
                for rid, (brain, score) in result.items()
            }
        return result

    def _vector_search(self, vector_index):
        """Execute vector search via VectorIndex.

        Returns dict: {rid: vector_score_normalized}
        """

        class QueryRecord:
            def __init__(self, text):
                self.keys = [text]

        record = QueryRecord(self.search_text)
        bucket = vector_index.query_index(record)

        if bucket is None:
            return {}

        result = {}
        for rid, int_score in bucket.items():
            result[rid] = float(int_score) / 100_000_000.0
        return result

    def _get_brain_by_rid(self, catalog, rid):
        """Get a catalog brain for a given RID."""
        try:
            path = catalog.getpath(rid)
            results = catalog.searchResults(path={"query": path, "depth": 0})
            if results:
                return results[0]
        except Exception:
            logger.debug("Could not resolve brain for RID %s", rid)
        return None

    def _prepare_vector_search(self, catalog):
        """Prepare and execute vector search if possible.

        Returns (vector_results, keyword_ratio) tuple.
        Sets self.vector_message and self.vector_index_name as side effects.
        """
        if not self._is_vectorsearch_available():
            self.vector_message = (
                "collective.vectorsearch is not installed. "
                "Showing keyword-only results."
            )
            return {}, 100

        if not self.vector_enabled:
            self.vector_message = (
                "Vector search is disabled in settings. "
                "Enable it in the Reranker control panel."
            )
            return {}, 100

        vector_index = self._find_vector_index(catalog)
        if vector_index is None:
            self.vector_message = (
                "No VectorIndex found in catalog. Please add a VectorIndex."
            )
            return {}, 100

        self.vector_index_name = vector_index.id
        try:
            return self._vector_search(vector_index), self.keyword_ratio
        except Exception as e:
            self.vector_message = f"Vector search error: {e}"
            return {}, 100

    def _compute_rrf_scores(self, keyword_results, vector_results):
        """Compute RRF (Reciprocal Rank Fusion) scores from rank positions.

        Returns dict: {rid: (keyword_rrf, vector_rrf)}
        """
        k = self.RRF_K

        # Sort keyword results by score descending → assign ranks
        kw_ranked = sorted(
            keyword_results.keys(),
            key=lambda rid: keyword_results[rid][1],
            reverse=True,
        )
        kw_rrf = {}
        for rank, rid in enumerate(kw_ranked, start=1):
            kw_rrf[rid] = 1.0 / (k + rank)

        # Sort vector results by score descending → assign ranks
        vec_ranked = sorted(
            vector_results.keys(),
            key=lambda rid: vector_results[rid],
            reverse=True,
        )
        vec_rrf = {}
        for rank, rid in enumerate(vec_ranked, start=1):
            vec_rrf[rid] = 1.0 / (k + rank)

        return kw_rrf, vec_rrf

    def _search_hybrid(self):
        """Execute hybrid search combining keyword and vector results."""
        catalog = getToolByName(self.context, "portal_catalog")
        now = DateTime()
        reranker_settings = RerankerSettings()

        # Step 1: Keyword search (always)
        keyword_results = self._keyword_search(catalog)

        # Step 2: Vector search (if available and enabled)
        vector_results, keyword_ratio = self._prepare_vector_search(catalog)

        self.effective_keyword_ratio = keyword_ratio
        self.effective_vector_ratio = 100 - keyword_ratio

        # Step 3: Compute combined scores
        kw = keyword_ratio / 100.0
        vw = 1.0 - kw
        use_rrf = self.scoring_mode == "rrf"

        kw_rrf = {}
        vec_rrf = {}
        if use_rrf and vector_results:
            kw_rrf, vec_rrf = self._compute_rrf_scores(keyword_results, vector_results)

        all_rids = set(keyword_results.keys()) | set(vector_results.keys())
        results = []

        for rid in all_rids:
            kw_data = keyword_results.get(rid)
            vs = vector_results.get(rid, 0.0)

            if kw_data is not None:
                brain, ks = kw_data
            else:
                ks = 0.0
                brain = self._get_brain_by_rid(catalog, rid)
                if brain is None:
                    continue

            if rid in keyword_results and rid in vector_results:
                source = "both"
            elif rid in keyword_results:
                source = "keyword"
            else:
                source = "vector"

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

            modified = getattr(brain, "modified", None)
            modified_str = modified.strftime("%Y-%m-%d %H:%M") if modified else "-"

            entry = {
                "title": brain.Title or "(no title)",
                "url": brain.getURL(),
                "portal_type": brain.portal_type,
                "modified": modified_str,
                "age_days": f"{age_days:.1f}",
                "keyword_score": f"{ks:.4f}",
                "vector_score": f"{vs:.4f}",
                "combined_score": f"{combined:.6f}",
                "boost": f"{boost:.2f}",
                "decay": f"{decay:.4f}",
                "final_score": f"{final_score:.6f}",
                "source": source,
            }
            if use_rrf and vector_results:
                entry["keyword_rrf"] = f"{kw_rrf.get(rid, 0.0):.6f}"
                entry["vector_rrf"] = f"{vec_rrf.get(rid, 0.0):.6f}"
            results.append(entry)

        results.sort(key=lambda x: float(x["final_score"]), reverse=True)

        for i, r in enumerate(results, start=1):
            r["rank"] = i

        return results
