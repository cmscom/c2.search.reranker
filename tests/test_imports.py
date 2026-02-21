"""Diagnostic tests to identify import failures on Plone 5.2.

These are UNIT tests that don't require the integration layer,
so they run even when ZCML loading fails.
"""

import importlib
import sys

import pytest


class TestModuleImports:
    """Test that all modules can be imported without errors."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "c2.search.reranker",
            "c2.search.reranker.interfaces",
            "c2.search.reranker.reranker",
            "c2.search.reranker.search",
            "c2.search.reranker.browser.search_override",
            "c2.search.reranker.browser.hybrid_search",
            "c2.search.reranker.services",
            "c2.search.reranker.services.search",
        ],
    )
    def test_import_module(self, module_name):
        """Module should be importable without errors."""
        try:
            mod = importlib.import_module(module_name)
            assert mod is not None
        except Exception as exc:
            pytest.fail(f"Failed to import {module_name}: {type(exc).__name__}: {exc}")


class TestZCMLDependencies:
    """Test that ZCML dependencies are available."""

    def test_plone_rest_service_directive(self):
        """plone.rest should provide the plone:service ZCML directive."""
        import plone.rest  # noqa: F401

    def test_plone_restapi_search_handler(self):
        """plone.restapi.search.handler.SearchHandler should be importable."""
        from plone.restapi.search.handler import SearchHandler  # noqa: F401

    def test_plone_restapi_search_utils(self):
        """plone.restapi.search.utils.unflatten_dotted_dict should exist."""
        from plone.restapi.search.utils import unflatten_dotted_dict  # noqa: F401

    def test_cmfplone_search_classes(self):
        """Products.CMFPlone.browser.search should have required classes."""
        from Products.CMFPlone.browser.search import AjaxSearch  # noqa: F401
        from Products.CMFPlone.browser.search import Search  # noqa: F401
        from Products.CMFPlone.browser.search import SortOption  # noqa: F401

    def test_batch_import(self):
        """Batch class should be importable (Plone 5.2 or 6)."""
        try:
            from plone.base.batch import Batch

            source = "plone.base.batch"
        except ImportError:
            from Products.CMFPlone.PloneBatch import Batch

            source = "Products.CMFPlone.PloneBatch"
        assert Batch is not None, f"Batch imported from {source}"

    def test_zctextindex_parseError(self):
        """Products.ZCTextIndex.ParseTree.ParseError should exist."""
        from Products.ZCTextIndex.ParseTree import ParseError  # noqa: F401

    def test_content_listing(self):
        """plone.app.contentlisting.interfaces.IContentListing should exist."""
        from plone.app.contentlisting.interfaces import IContentListing  # noqa: F401

    def test_viewpagetemplatefile(self):
        """ViewPageTemplateFile should work with CMFPlone's search.pt."""
        import os

        import Products.CMFPlone.browser
        from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

        template_path = os.path.join(
            os.path.dirname(Products.CMFPlone.browser.__file__),
            "templates",
            "search.pt",
        )
        assert os.path.isfile(template_path), f"Template not found: {template_path}"
        # Try creating the ViewPageTemplateFile
        vpt = ViewPageTemplateFile(template_path)
        assert vpt is not None


class TestZCMLLoading:
    """Test ZCML loading directly."""

    def test_python_version(self):
        """Report Python version for debugging."""
        assert sys.version_info >= (3, 8), f"Python {sys.version}"

    def test_zcml_condition_installed(self):
        """zcml:condition 'installed' verb should work."""
        from zope.configuration.config import ConfigurationContext
        from zope.configuration.xmlconfig import ConfigurationHandler

        context = ConfigurationContext()
        handler = ConfigurationHandler(context, testing=True)
        # zope.interface is always available
        assert handler.evaluateCondition("installed zope.interface") is True
        assert handler.evaluateCondition("not-installed zope.interface") is False
        # plone.nonexistent should not be available
        assert handler.evaluateCondition("installed plone.nonexistent") is False
        assert handler.evaluateCondition("not-installed plone.nonexistent") is True
