# Fix plone.supermodel < 1.7.0 finalizeSchemas TypeError on Plone 5.2.
# plone.dexterity 2.11.0 introduces Provides objects in schema.dependents,
# but sorted() can't compare Provides with SchemaClass.
# See: https://github.com/plone/plone.supermodel/pull/55
try:
    from zope.interface.declarations import Provides

    if not hasattr(Provides, "__lt__"):
        Provides.__lt__ = lambda self, other: id(self) < id(other)
except ImportError:
    pass

from c2.search.reranker.testing import ACCEPTANCE_TESTING
from c2.search.reranker.testing import FUNCTIONAL_TESTING
from c2.search.reranker.testing import INTEGRATION_TESTING
from pytest_plone import fixtures_factory


pytest_plugins = ["pytest_plone"]


globals().update(
    fixtures_factory((
        (ACCEPTANCE_TESTING, "acceptance"),
        (FUNCTIONAL_TESTING, "functional"),
        (INTEGRATION_TESTING, "integration"),
    ))
)
