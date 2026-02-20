"""Browser view for hybrid search combining keyword and vector search."""

from c2.search.reranker.interfaces import IRerankerSettings
from c2.search.reranker.reranker import (
    RerankerSettings,
    calculate_time_decay,
    get_content_age_days,
)
from c2.search.reranker.search import (
    compute_rrf_scores,
    find_vector_index,
    get_brain_by_rid,
    is_vectorsearch_available,
    keyword_search,
    vector_search,
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

    def _prepare_vector_search(self, catalog):
        """Prepare and execute vector search if possible.

        Returns (vector_results, keyword_ratio) tuple.
        Sets self.vector_message and self.vector_index_name as side effects.
        """
        if not is_vectorsearch_available():
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

        vector_index = find_vector_index(catalog)
        if vector_index is None:
            self.vector_message = (
                "No VectorIndex found in catalog. Please add a VectorIndex."
            )
            return {}, 100

        self.vector_index_name = vector_index.id
        try:
            return vector_search(vector_index, self.search_text), self.keyword_ratio
        except Exception as e:
            self.vector_message = f"Vector search error: {e}"
            return {}, 100

    def _search_hybrid(self):
        """Execute hybrid search combining keyword and vector results."""
        catalog = getToolByName(self.context, "portal_catalog")
        now = DateTime()
        reranker_settings = RerankerSettings()

        # Step 1: Keyword search (always)
        keyword_results = keyword_search(catalog, self.search_text)

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
            kw_rrf, vec_rrf = compute_rrf_scores(keyword_results, vector_results)

        all_rids = set(keyword_results.keys()) | set(vector_results.keys())
        results = []

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
