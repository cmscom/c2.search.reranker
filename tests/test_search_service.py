"""Integration tests for the custom @search REST API service with reranking."""

from c2.search.reranker.interfaces import IRerankerSettings
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

import pytest


def _make_service(context, request):
    """Create and configure a RerankerSearchGet service instance."""
    from c2.search.reranker.services.search import RerankerSearchGet

    service = RerankerSearchGet.__new__(RerankerSearchGet)
    service.context = context
    service.request = request
    return service


class TestRerankerSearchService:
    """Test the custom @search REST API service."""

    @pytest.fixture(autouse=True)
    def _setup(self, integration):
        self.portal = integration["portal"]
        self.request = integration["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def _get_settings(self):
        registry = getUtility(IRegistry)
        return registry.forInterface(IRerankerSettings)

    def _set_reranker_enabled(self, enabled):
        settings = self._get_settings()
        settings.reranker_enabled = enabled

    def test_reranker_enabled_setting_exists(self):
        """The reranker_enabled setting should exist in the registry."""
        settings = self._get_settings()
        assert hasattr(settings, "reranker_enabled")
        assert settings.reranker_enabled is False

    def test_disabled_delegates_to_default(self):
        """When disabled, @search should work normally."""
        self._set_reranker_enabled(False)
        api.content.create(
            container=self.portal,
            type="Document",
            id="test-doc-service",
            title="Service Test Gamma Document",
        )

        self.request.form["SearchableText"] = "Gamma"
        service = _make_service(self.portal, self.request)
        result = service.reply()
        assert isinstance(result, dict)
        assert "items" in result or "items_total" in result

    def test_enabled_returns_results(self):
        """When enabled, @search should return reranked results."""
        self._set_reranker_enabled(True)
        api.content.create(
            container=self.portal,
            type="Document",
            id="test-doc-reranked",
            title="Reranked Service Test Delta Document",
        )

        self.request.form["SearchableText"] = "Delta"
        service = _make_service(self.portal, self.request)
        result = service.reply()
        assert isinstance(result, dict)
        assert "items" in result
        assert "items_total" in result

    def test_empty_search_returns_structure(self):
        """Empty search should return proper JSON structure."""
        self._set_reranker_enabled(True)

        self.request.form["SearchableText"] = "nonexistent_xyzzy_12345"
        service = _make_service(self.portal, self.request)
        result = service.reply()
        assert isinstance(result, dict)
        assert result.get("items_total", 0) == 0

    def test_no_searchable_text_delegates(self):
        """When no SearchableText, should delegate to normal search."""
        self._set_reranker_enabled(True)

        service = _make_service(self.portal, self.request)
        result = service.reply()
        assert isinstance(result, (dict, list))
