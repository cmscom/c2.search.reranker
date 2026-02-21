"""Control panel for c2.search.reranker."""

from c2.search.reranker import _
from c2.search.reranker.interfaces import IRerankerSettings
from plone.app.registry.browser import controlpanel
from z3c.form.browser.checkbox import SingleCheckBoxFieldWidget


class RerankerSettingsEditForm(controlpanel.RegistryEditForm):
    """Reranker settings form."""

    schema = IRerankerSettings
    id = "RerankerSettingsEditForm"
    label = _("label_reranker_settings", default="Search Reranker Settings")
    description = _(
        "help_reranker_settings",
        default="Configure search result reranking, including vector search "
        "integration and content type group boosting.",
    )

    def updateFields(self):
        super().updateFields()
        self.fields["reranker_enabled"].widgetFactory = SingleCheckBoxFieldWidget
        self.fields["vector_search_enabled"].widgetFactory = SingleCheckBoxFieldWidget


class RerankerSettingsControlPanel(controlpanel.ControlPanelFormWrapper):
    """Reranker settings control panel."""

    form = RerankerSettingsEditForm
