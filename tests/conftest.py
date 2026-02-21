# Fix plone.supermodel < 1.7.0 finalizeSchemas TypeError on Plone 5.2.
# plone.dexterity 2.11.0 introduces Provides objects in schema.dependents,
# but plone.supermodel < 1.7.0's walk() yields all objects (including Provides),
# causing sorted() to fail with TypeError when comparing Provides with SchemaClass.
# We backport the fix from plone.supermodel >= 1.7.0: filter to SchemaClass only.
# See: https://github.com/plone/plone.supermodel/pull/55
try:
    import pkg_resources

    _version = tuple(
        int(x)
        for x in pkg_resources.get_distribution("plone.supermodel").version.split(".")[
            :3
        ]
    )
    if _version < (1, 7, 0):
        import logging

        from plone.supermodel import model as _psm
        from plone.supermodel.model import SchemaClass
        from zope.interface.interface import InterfaceClass

        _logger = logging.getLogger("plone.supermodel")

        def _patched_finalizeSchemas(parent=None):
            if parent is None:
                parent = _psm.Schema
            if not isinstance(parent, SchemaClass):
                raise TypeError(
                    "Only instances of plone.supermodel.model.SchemaClass "
                    "can be finalized."
                )

            def walk(schema):
                if isinstance(schema, SchemaClass):
                    yield schema
                try:
                    children = schema.dependents.keys()
                except AttributeError:
                    children = ()
                for child in children:
                    yield from walk(child)

            schemas = set(walk(parent))
            for schema in sorted(schemas):
                if hasattr(schema, "_SchemaClass_finalize"):
                    schema._SchemaClass_finalize()
                elif isinstance(schema, InterfaceClass):
                    _logger.warn(
                        f"{schema.__module__}.{schema.__name__} is not an "
                        f"instance of SchemaClass. This can happen if the "
                        f"first base class of a schema is not a SchemaClass. "
                        f"See https://bugs.launchpad.net/zope.interface/+bug/791218"
                    )

        _psm.finalizeSchemas = _patched_finalizeSchemas
except Exception:  # noqa: S110
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
