"""Integration tests for the classic @@search view override with reranking."""

from c2.search.reranker.browser.search_override import RERANKER_SORT_KEY
from c2.search.reranker.interfaces import IBrowserLayer
from c2.search.reranker.interfaces import IRerankerSettings
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.interface import alsoProvides

import pytest


class TestRerankedSearchView:
    """Test the classic @@search view override."""

    @pytest.fixture(autouse=True)
    def _setup(self, integration):
        self.portal = integration["portal"]
        self.request = integration["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        # Ensure IBrowserLayer is marked on the request.
        # On Plone 5.2, plone.app.testing does not automatically apply
        # registered browser layers to the test request.
        alsoProvides(self.request, IBrowserLayer)

    def _set_reranker_enabled(self, enabled):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IRerankerSettings)
        settings.reranker_enabled = enabled

    def _get_view(self):
        return api.content.get_view(
            name="search",
            context=self.portal,
            request=self.request,
        )

    def test_search_view_registered(self):
        """The @@search view should be our override when layer is active."""
        from c2.search.reranker.browser.search_override import RerankedSearch

        view = self._get_view()
        assert isinstance(view, RerankedSearch)

    def test_disabled_returns_normal_results(self):
        """When disabled, @@search should return normal catalog results."""
        self._set_reranker_enabled(False)
        api.content.create(
            container=self.portal,
            type="Document",
            id="test-classic-doc",
            title="Classic Search Test Epsilon Document",
        )

        self.request.form["SearchableText"] = "Epsilon"
        results = self._get_view().results(batch=False)
        assert len(results) > 0

    def test_enabled_returns_reranked_results(self):
        """When enabled with reranker sort, should return reranked results."""
        self._set_reranker_enabled(True)
        api.content.create(
            container=self.portal,
            type="Document",
            id="test-classic-reranked",
            title="Classic Reranked Test Zeta Document",
        )

        self.request.form["SearchableText"] = "Zeta"
        self.request.form["sort_on"] = RERANKER_SORT_KEY
        results = self._get_view().results(batch=False)
        assert len(results) > 0

    def test_enabled_with_batching(self):
        """When enabled, @@search batching should work correctly."""
        self._set_reranker_enabled(True)
        for i in range(5):
            api.content.create(
                container=self.portal,
                type="Document",
                id=f"test-batch-doc-{i}",
                title=f"Batch Test Eta {i} Document",
            )

        self.request.form["SearchableText"] = "Eta"
        self.request.form["sort_on"] = RERANKER_SORT_KEY
        results = self._get_view().results(batch=True, b_size=2, b_start=0)
        # Batch should limit to b_size
        assert len(list(results)) <= 2

    def test_no_searchable_text_falls_back(self):
        """When no SearchableText, should fall back to normal catalog."""
        self._set_reranker_enabled(True)
        self.request.form["sort_on"] = RERANKER_SORT_KEY
        # Without SearchableText, results() should handle gracefully
        results = self._get_view().results(batch=False)
        # Should return an empty or normal result
        assert results is not None

    def test_enabled_relevance_sort_uses_normal_catalog(self):
        """When enabled but sort_on=relevance, should use normal catalog."""
        self._set_reranker_enabled(True)
        api.content.create(
            container=self.portal,
            type="Document",
            id="test-relevance-sort",
            title="Relevance Sort Test Theta Document",
        )

        self.request.form["SearchableText"] = "Theta"
        self.request.form["sort_on"] = "relevance"
        results = self._get_view().results(batch=False)
        assert len(results) > 0

    def test_enabled_default_sort_is_reranker(self):
        """When enabled and no sort specified, should default to reranker."""
        self._set_reranker_enabled(True)
        api.content.create(
            container=self.portal,
            type="Document",
            id="test-default-sort",
            title="Default Sort Test Iota Document",
        )

        self.request.form["SearchableText"] = "Iota"
        # No sort_on in request.form — should default to reranker
        results = self._get_view().results(batch=False)
        assert len(results) > 0

    def test_sort_options_disabled_normal(self):
        """When disabled, sort_options should return standard options."""
        self._set_reranker_enabled(False)
        view = self._get_view()
        options = view.sort_options()
        sortkeys = [opt.sortkey for opt in options]
        assert sortkeys == ["relevance", "Date", "sortable_title"]

    def test_sort_options_enabled_has_reranker(self):
        """When enabled, sort_options should include reranker as first."""
        self._set_reranker_enabled(True)
        view = self._get_view()
        options = view.sort_options()
        sortkeys = [opt.sortkey for opt in options]
        assert sortkeys == [RERANKER_SORT_KEY, "relevance", "Date", "sortable_title"]

    def test_sort_options_enabled_default_selected(self):
        """When enabled with no sort_on, reranker should be the default."""
        self._set_reranker_enabled(True)
        view = self._get_view()
        view.sort_options()
        assert self.request.form.get("sort_on") == RERANKER_SORT_KEY


class TestRerankedAjaxSearchView:
    """Test the @@ajax-search view override."""

    @pytest.fixture(autouse=True)
    def _setup(self, integration):
        self.portal = integration["portal"]
        self.request = integration["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        alsoProvides(self.request, IBrowserLayer)

    def test_ajax_search_view_registered(self):
        """The @@ajax-search view should be our override."""
        from c2.search.reranker.browser.search_override import RerankedAjaxSearch

        view = api.content.get_view(
            name="ajax-search",
            context=self.portal,
            request=self.request,
        )
        assert isinstance(view, RerankedAjaxSearch)
