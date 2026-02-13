"""REST API integration for c2.search.reranker control panel."""

from c2.search.reranker import _
from c2.search.reranker.interfaces import IRerankerSettings
from plone.restapi.controlpanels import RegistryConfigletPanel
from zope.component import adapter
from zope.interface import Interface


@adapter(Interface, Interface)
class RerankerControlPanel(RegistryConfigletPanel):
    """REST API control panel for reranker settings."""

    schema = IRerankerSettings
    schema_prefix = None
    configlet_id = "reranker"
    configlet_category_id = "Products"
    title = _("label_reranker_settings", default="Search Reranker Settings")
    group = "Products"
