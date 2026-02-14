"""Core reranking engine for search results.

Provides two features:
  Feature 1: Content type boost weighting
  Feature 2: Half-life time decay weighting

Score formula:
  final_score = original_score * boost * decay
"""

from c2.search.reranker import logger
from c2.search.reranker.interfaces import IRerankerSettings
from DateTime import DateTime
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

import math


# Group names matching control panel field naming convention
GROUP_NAMES = ("general", "announcements", "knowledge", "other")

# Defaults for content types not assigned to any group
DEFAULT_BOOST = 1.0
DEFAULT_HALFLIFE = 60


class RerankerSettings:
    """Reads reranker settings from plone.app.registry and builds
    a portal_type -> (boost, halflife) mapping."""

    def __init__(self):
        registry = getUtility(IRegistry)
        self._settings = registry.forInterface(IRerankerSettings)
        self._type_map = {}
        self._build_type_map()

    def _build_type_map(self):
        """Build mapping from portal_type to (boost, halflife)."""
        for group_name in GROUP_NAMES:
            content_types = (
                getattr(
                    self._settings,
                    f"group_{group_name}_content_types",
                    None,
                )
                or ()
            )
            boost = (
                getattr(self._settings, f"group_{group_name}_boost", None)
                or DEFAULT_BOOST
            )
            halflife = (
                getattr(
                    self._settings, f"group_{group_name}_halflife", None
                )
                or DEFAULT_HALFLIFE
            )
            for ct in content_types:
                self._type_map[ct] = (boost, halflife)

    def get_boost(self, portal_type):
        """Return boost factor for a portal_type (1.0 if not assigned)."""
        if portal_type in self._type_map:
            return self._type_map[portal_type][0]
        return DEFAULT_BOOST

    def get_halflife(self, portal_type):
        """Return halflife in days for a portal_type (60 if not assigned)."""
        if portal_type in self._type_map:
            return self._type_map[portal_type][1]
        return DEFAULT_HALFLIFE


# --- Feature 2: Half-life time decay ---


def calculate_time_decay(age_in_days, halflife_days):
    """Calculate exponential time decay factor.

    Formula: decay = 0.5 ^ (age_in_days / halflife_days)

    Args:
        age_in_days: Days since content was modified. Negative values
            are clamped to 0.
        halflife_days: Days for the score to halve. Must be >= 1.

    Returns:
        Float between 0.0 and 1.0.
    """
    if halflife_days < 1:
        halflife_days = 1
    if age_in_days < 0:
        age_in_days = 0
    return math.pow(0.5, age_in_days / halflife_days)


def get_content_age_days(brain, now=None):
    """Calculate content age in days from brain.modified.

    Args:
        brain: A ZCatalog brain object.
        now: Optional DateTime for current time (for testing).

    Returns:
        Age in days as float. Returns 0.0 if modified is not available.
    """
    if now is None:
        now = DateTime()

    modified = getattr(brain, "modified", None)
    if modified is None:
        return 0.0

    try:
        age = float(now - modified)
    except (TypeError, ValueError):
        logger.warning(
            "Could not compute age for %s",
            getattr(brain, "getPath", lambda: "unknown")(),
        )
        return 0.0

    return max(0.0, age)


# --- Combined reranking ---


def rerank_brains(brains, now=None):
    """Rerank catalog brains using content type boost and time decay.

    Args:
        brains: List of catalog brain objects.
        now: Optional DateTime for current time (for testing).

    Returns:
        List of (brain, score_details) tuples sorted by final_score
        descending. score_details is a dict with keys:
        original_score, boost, decay, final_score.
    """
    settings = RerankerSettings()
    if now is None:
        now = DateTime()

    scored = []
    for brain in brains:
        portal_type = brain.portal_type

        # Original relevance score from ZCTextIndex
        original_score = getattr(
            brain, "data_record_normalized_score_", None
        )
        if original_score is None or original_score == 0:
            original_score = 1.0
        else:
            original_score = float(original_score)

        # Feature 1: Content type boost
        boost = settings.get_boost(portal_type)

        # Feature 2: Time decay
        halflife = settings.get_halflife(portal_type)
        age_days = get_content_age_days(brain, now=now)
        decay = calculate_time_decay(age_days, halflife)

        final_score = original_score * boost * decay

        score_details = {
            "original_score": original_score,
            "boost": boost,
            "decay": decay,
            "final_score": final_score,
        }
        scored.append((brain, score_details))

    scored.sort(key=lambda x: x[1]["final_score"], reverse=True)
    return scored
