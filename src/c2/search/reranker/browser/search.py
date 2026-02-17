"""Temporary browser view for testing the reranking algorithm."""

from c2.search.reranker.reranker import rerank_brains
from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView


class RerankerSearchView(BrowserView):
    """Browser view that displays reranked search results with score details.

    Access via: @@reranker-search?SearchableText=keyword
    """

    def __call__(self):
        self.search_text = self.request.form.get("SearchableText", "")
        self.results = []
        self.error = ""

        if self.search_text:
            try:
                self.results = self._search_and_rerank()
            except Exception as e:
                self.error = str(e)

        return self.index()

    def _search_and_rerank(self):
        """Execute catalog search and apply reranking."""
        catalog = getToolByName(self.context, "portal_catalog")
        now = DateTime()

        query = {
            "SearchableText": self.search_text,
            "sort_limit": 200,
        }
        brains = list(catalog.searchResults(**query))

        if not brains:
            return []

        ranked = rerank_brains(brains, now=now)

        results = []
        for rank, (brain, scores) in enumerate(ranked, start=1):
            modified = getattr(brain, "modified", None)
            modified_str = modified.strftime("%Y-%m-%d %H:%M") if modified else "-"
            age_days = float(now - modified) if modified else 0.0

            results.append({
                "rank": rank,
                "title": brain.Title or "(no title)",
                "url": brain.getURL(),
                "portal_type": brain.portal_type,
                "modified": modified_str,
                "age_days": f"{age_days:.1f}",
                "original_score": f"{scores['original_score']:.4f}",
                "boost": f"{scores['boost']:.2f}",
                "decay": f"{scores['decay']:.4f}",
                "final_score": f"{scores['final_score']:.4f}",
            })

        return results
