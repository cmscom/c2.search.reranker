"""Module where all interfaces, events and exceptions live."""

from c2.search.reranker import _
from plone.supermodel import model
from plone.supermodel.directives import fieldset
from zope import schema
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

scoring_mode_vocabulary = SimpleVocabulary([
    SimpleTerm(
        "rrf",
        "rrf",
        "RRF (Reciprocal Rank Fusion) - Combine by rank position",
    ),
    SimpleTerm(
        "score",
        "score",
        "Score - Weighted average of normalized scores",
    ),
])


class IBrowserLayer(IDefaultBrowserLayer):
    """Marker interface that defines a browser layer."""


class IRerankerSettings(model.Schema):
    """Settings for the search reranker."""

    # --- General Settings (default fieldset) ---

    vector_search_enabled = schema.Bool(
        title=_("label_vector_search_enabled", default="Enable vector search"),
        description=_(
            "help_vector_search_enabled",
            default="If selected, vector search (provided by "
            "collective.vectorsearch) will be used in combination "
            "with keyword search. Requires collective.vectorsearch "
            "to be installed.",
        ),
        required=False,
        default=False,
    )

    keyword_search_ratio = schema.Int(
        title=_(
            "label_keyword_search_ratio",
            default="Keyword search ratio (%)",
        ),
        description=_(
            "help_keyword_search_ratio",
            default="The percentage of weight given to keyword search "
            "results (0-100). The remaining percentage is given "
            "to vector search. For example, 70 means 70%% keyword "
            "search and 30%% vector search. Only effective when "
            "vector search is enabled.",
        ),
        required=True,
        default=50,
        min=0,
        max=100,
    )

    scoring_mode = schema.Choice(
        title=_(
            "label_scoring_mode",
            default="Scoring mode",
        ),
        description=_(
            "help_scoring_mode",
            default="The method used to combine keyword and vector search "
            "scores. 'RRF' (Reciprocal Rank Fusion) combines results "
            "based on rank position, which is robust against score "
            "scale differences. 'Score' uses weighted average of "
            "normalized scores. Only effective when vector search "
            "is enabled.",
        ),
        vocabulary=scoring_mode_vocabulary,
        required=True,
        default="rrf",
    )

    # --- General Pages Group ---

    fieldset(
        "group_general",
        label=_("label_group_general", default="General Pages"),
        fields=[
            "group_general_content_types",
            "group_general_boost",
            "group_general_halflife",
        ],
    )

    group_general_content_types = schema.Tuple(
        title=_(
            "label_group_general_content_types",
            default="Content types",
        ),
        description=_(
            "help_group_general_content_types",
            default="Select the content types for the General Pages group.",
        ),
        required=False,
        default=(),
        missing_value=(),
        value_type=schema.Choice(
            source="plone.app.vocabularies.ReallyUserFriendlyTypes"
        ),
    )

    group_general_boost = schema.Float(
        title=_("label_group_general_boost", default="Boost rate"),
        description=_(
            "help_group_general_boost",
            default="The boost multiplier for search results in this group. "
            "Values greater than 1.0 increase relevance, values less "
            "than 1.0 decrease it.",
        ),
        required=True,
        default=1.0,
    )

    group_general_halflife = schema.Int(
        title=_("label_group_general_halflife", default="Half-life (days)"),
        description=_(
            "help_group_general_halflife",
            default="The number of days after which the time-decay boost "
            "is halved. A higher value means content stays relevant longer.",
        ),
        required=True,
        default=60,
        min=1,
    )

    # --- Announcements Group ---

    fieldset(
        "group_announcements",
        label=_("label_group_announcements", default="Announcements"),
        fields=[
            "group_announcements_content_types",
            "group_announcements_boost",
            "group_announcements_halflife",
        ],
    )

    group_announcements_content_types = schema.Tuple(
        title=_(
            "label_group_announcements_content_types",
            default="Content types",
        ),
        description=_(
            "help_group_announcements_content_types",
            default="Select the content types for the Announcements group.",
        ),
        required=False,
        default=(),
        missing_value=(),
        value_type=schema.Choice(
            source="plone.app.vocabularies.ReallyUserFriendlyTypes"
        ),
    )

    group_announcements_boost = schema.Float(
        title=_("label_group_announcements_boost", default="Boost rate"),
        description=_(
            "help_group_announcements_boost",
            default="The boost multiplier for search results in this group. "
            "Values greater than 1.0 increase relevance, values less "
            "than 1.0 decrease it.",
        ),
        required=True,
        default=1.0,
    )

    group_announcements_halflife = schema.Int(
        title=_(
            "label_group_announcements_halflife",
            default="Half-life (days)",
        ),
        description=_(
            "help_group_announcements_halflife",
            default="The number of days after which the time-decay boost "
            "is halved. A higher value means content stays relevant longer.",
        ),
        required=True,
        default=60,
        min=1,
    )

    # --- Knowledge Group ---

    fieldset(
        "group_knowledge",
        label=_("label_group_knowledge", default="Knowledge"),
        fields=[
            "group_knowledge_content_types",
            "group_knowledge_boost",
            "group_knowledge_halflife",
        ],
    )

    group_knowledge_content_types = schema.Tuple(
        title=_(
            "label_group_knowledge_content_types",
            default="Content types",
        ),
        description=_(
            "help_group_knowledge_content_types",
            default="Select the content types for the Knowledge group.",
        ),
        required=False,
        default=(),
        missing_value=(),
        value_type=schema.Choice(
            source="plone.app.vocabularies.ReallyUserFriendlyTypes"
        ),
    )

    group_knowledge_boost = schema.Float(
        title=_("label_group_knowledge_boost", default="Boost rate"),
        description=_(
            "help_group_knowledge_boost",
            default="The boost multiplier for search results in this group. "
            "Values greater than 1.0 increase relevance, values less "
            "than 1.0 decrease it.",
        ),
        required=True,
        default=1.0,
    )

    group_knowledge_halflife = schema.Int(
        title=_(
            "label_group_knowledge_halflife",
            default="Half-life (days)",
        ),
        description=_(
            "help_group_knowledge_halflife",
            default="The number of days after which the time-decay boost "
            "is halved. A higher value means content stays relevant longer.",
        ),
        required=True,
        default=60,
        min=1,
    )

    # --- Other Group ---

    fieldset(
        "group_other",
        label=_("label_group_other", default="Other"),
        fields=[
            "group_other_content_types",
            "group_other_boost",
            "group_other_halflife",
        ],
    )

    group_other_content_types = schema.Tuple(
        title=_(
            "label_group_other_content_types",
            default="Content types",
        ),
        description=_(
            "help_group_other_content_types",
            default="Select the content types for the Other group.",
        ),
        required=False,
        default=(),
        missing_value=(),
        value_type=schema.Choice(
            source="plone.app.vocabularies.ReallyUserFriendlyTypes"
        ),
    )

    group_other_boost = schema.Float(
        title=_("label_group_other_boost", default="Boost rate"),
        description=_(
            "help_group_other_boost",
            default="The boost multiplier for search results in this group. "
            "Values greater than 1.0 increase relevance, values less "
            "than 1.0 decrease it.",
        ),
        required=True,
        default=1.0,
    )

    group_other_halflife = schema.Int(
        title=_("label_group_other_halflife", default="Half-life (days)"),
        description=_(
            "help_group_other_halflife",
            default="The number of days after which the time-decay boost "
            "is halved. A higher value means content stays relevant longer.",
        ),
        required=True,
        default=60,
        min=1,
    )
