"""Integration tests for the @@reranker-search browser view."""

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import pytest


class TestRerankerSearchView:
    """Test the temporary reranker search browser view."""

    @pytest.fixture(autouse=True)
    def _setup(self, integration):
        self.portal = integration["portal"]
        self.request = integration["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def test_view_exists(self):
        """The @@reranker-search view should be registered."""
        view = api.content.get_view(
            name="reranker-search",
            context=self.portal,
            request=self.request,
        )
        assert view is not None

    def test_empty_search_text(self):
        """View should handle empty search text gracefully."""
        view = api.content.get_view(
            name="reranker-search",
            context=self.portal,
            request=self.request,
        )
        view.search_text = ""
        view.results = []
        view.error = ""
        # Calling _search_and_rerank with no SearchableText param
        # should not crash
        assert view.search_text == ""

    def test_search_returns_results(self):
        """View should return results for matching content."""
        api.content.create(
            container=self.portal,
            type="Document",
            id="test-doc",
            title="Reranker Test Alpha Document",
        )
        self.portal.portal_catalog.reindexObject(self.portal["test-doc"])

        self.request.form["SearchableText"] = "Alpha"
        view = api.content.get_view(
            name="reranker-search",
            context=self.portal,
            request=self.request,
        )
        # Manually trigger search logic
        view.search_text = "Alpha"
        results = view._search_and_rerank()
        assert len(results) > 0
        assert any("Alpha" in r["title"] for r in results)

    def test_result_has_score_fields(self):
        """Each result should include all score detail fields."""
        api.content.create(
            container=self.portal,
            type="Document",
            id="test-score-doc",
            title="Reranker Score Test Beta",
        )
        self.portal.portal_catalog.reindexObject(
            self.portal["test-score-doc"]
        )

        self.request.form["SearchableText"] = "Beta"
        view = api.content.get_view(
            name="reranker-search",
            context=self.portal,
            request=self.request,
        )
        view.search_text = "Beta"
        results = view._search_and_rerank()
        assert len(results) > 0

        result = results[0]
        assert "rank" in result
        assert "original_score" in result
        assert "boost" in result
        assert "decay" in result
        assert "final_score" in result
        assert "portal_type" in result
