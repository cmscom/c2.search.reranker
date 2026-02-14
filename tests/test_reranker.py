"""Unit tests for the reranking engine."""

from unittest.mock import MagicMock

from DateTime import DateTime

import math
import pytest


# --- Tests for calculate_time_decay ---


class TestCalculateTimeDecay:
    """Test the time decay formula: 0.5^(age_in_days / halflife_days)."""

    def test_zero_age_returns_one(self):
        from c2.search.reranker.reranker import calculate_time_decay

        assert calculate_time_decay(0, 60) == 1.0

    def test_age_equals_halflife_returns_half(self):
        from c2.search.reranker.reranker import calculate_time_decay

        assert calculate_time_decay(60, 60) == pytest.approx(0.5)

    def test_age_double_halflife_returns_quarter(self):
        from c2.search.reranker.reranker import calculate_time_decay

        assert calculate_time_decay(120, 60) == pytest.approx(0.25)

    def test_negative_age_clamped_to_zero(self):
        from c2.search.reranker.reranker import calculate_time_decay

        assert calculate_time_decay(-10, 60) == 1.0

    def test_very_large_age_approaches_zero(self):
        from c2.search.reranker.reranker import calculate_time_decay

        result = calculate_time_decay(10000, 60)
        assert result < 0.001

    def test_halflife_minimum_clamped_to_one(self):
        from c2.search.reranker.reranker import calculate_time_decay

        result = calculate_time_decay(1, 0)
        assert result == pytest.approx(0.5)

    def test_short_halflife_decays_faster(self):
        from c2.search.reranker.reranker import calculate_time_decay

        short = calculate_time_decay(30, 10)
        long_ = calculate_time_decay(30, 90)
        assert short < long_

    def test_one_day_age_with_halflife_365(self):
        from c2.search.reranker.reranker import calculate_time_decay

        result = calculate_time_decay(1, 365)
        expected = math.pow(0.5, 1 / 365)
        assert result == pytest.approx(expected)


# --- Tests for get_content_age_days ---


class TestGetContentAgeDays:
    """Test content age calculation from brain.modified."""

    def test_age_from_modified(self):
        from c2.search.reranker.reranker import get_content_age_days

        now = DateTime("2025-06-01 00:00:00 UTC")
        brain = MagicMock()
        brain.modified = DateTime("2025-05-01 00:00:00 UTC")

        age = get_content_age_days(brain, now=now)
        assert age == pytest.approx(31.0, abs=0.01)

    def test_missing_modified_returns_zero(self):
        from c2.search.reranker.reranker import get_content_age_days

        now = DateTime("2025-06-01 00:00:00 UTC")
        brain = MagicMock(spec=[])  # no attributes

        age = get_content_age_days(brain, now=now)
        assert age == 0.0

    def test_future_modified_clamped_to_zero(self):
        from c2.search.reranker.reranker import get_content_age_days

        now = DateTime("2025-06-01 00:00:00 UTC")
        brain = MagicMock()
        brain.modified = DateTime("2025-07-01 00:00:00 UTC")

        age = get_content_age_days(brain, now=now)
        assert age == 0.0

    def test_same_day_returns_zero(self):
        from c2.search.reranker.reranker import get_content_age_days

        now = DateTime("2025-06-01 12:00:00 UTC")
        brain = MagicMock()
        brain.modified = DateTime("2025-06-01 12:00:00 UTC")

        age = get_content_age_days(brain, now=now)
        assert age == 0.0


# --- Tests for RerankerSettings ---


class TestRerankerSettings:
    """Test settings reading from the registry."""

    @pytest.fixture(autouse=True)
    def _setup(self, integration):
        self.portal = integration["portal"]

    def test_default_boost_for_unassigned_type(self):
        from c2.search.reranker.reranker import RerankerSettings

        settings = RerankerSettings()
        assert settings.get_boost("UnknownType") == 1.0

    def test_default_halflife_for_unassigned_type(self):
        from c2.search.reranker.reranker import RerankerSettings

        settings = RerankerSettings()
        assert settings.get_halflife("UnknownType") == 60

    def test_configured_boost(self):
        from c2.search.reranker.interfaces import IRerankerSettings
        from c2.search.reranker.reranker import RerankerSettings
        from plone.registry.interfaces import IRegistry
        from zope.component import getUtility

        registry = getUtility(IRegistry)
        settings = registry.forInterface(IRerankerSettings)
        settings.group_general_content_types = ("Document",)
        settings.group_general_boost = 2.5

        rs = RerankerSettings()
        assert rs.get_boost("Document") == 2.5

    def test_configured_halflife(self):
        from c2.search.reranker.interfaces import IRerankerSettings
        from c2.search.reranker.reranker import RerankerSettings
        from plone.registry.interfaces import IRegistry
        from zope.component import getUtility

        registry = getUtility(IRegistry)
        settings = registry.forInterface(IRerankerSettings)
        settings.group_announcements_content_types = ("News Item",)
        settings.group_announcements_halflife = 14

        rs = RerankerSettings()
        assert rs.get_halflife("News Item") == 14

    def test_multiple_groups(self):
        from c2.search.reranker.interfaces import IRerankerSettings
        from c2.search.reranker.reranker import RerankerSettings
        from plone.registry.interfaces import IRegistry
        from zope.component import getUtility

        registry = getUtility(IRegistry)
        settings = registry.forInterface(IRerankerSettings)
        settings.group_general_content_types = ("Document",)
        settings.group_general_boost = 1.5
        settings.group_announcements_content_types = ("News Item",)
        settings.group_announcements_boost = 0.8

        rs = RerankerSettings()
        assert rs.get_boost("Document") == 1.5
        assert rs.get_boost("News Item") == 0.8
        assert rs.get_boost("File") == 1.0  # unassigned


# --- Tests for rerank_brains ---


class TestRerankBrains:
    """Test the combined reranking function."""

    @pytest.fixture(autouse=True)
    def _setup(self, integration):
        self.portal = integration["portal"]

    def _make_brain(self, portal_type, modified, score=None):
        brain = MagicMock()
        brain.portal_type = portal_type
        brain.modified = modified
        if score is not None:
            brain.data_record_normalized_score_ = score
        else:
            brain.data_record_normalized_score_ = None
        brain.getPath.return_value = f"/plone/{portal_type.lower()}"
        return brain

    def test_boost_affects_ranking(self):
        """Higher boost should rank higher when other factors are equal."""
        from c2.search.reranker.interfaces import IRerankerSettings
        from c2.search.reranker.reranker import rerank_brains
        from plone.registry.interfaces import IRegistry
        from zope.component import getUtility

        registry = getUtility(IRegistry)
        settings = registry.forInterface(IRerankerSettings)
        settings.group_general_content_types = ("Document",)
        settings.group_general_boost = 3.0
        settings.group_announcements_content_types = ("News Item",)
        settings.group_announcements_boost = 0.5

        now = DateTime("2025-06-01 00:00:00 UTC")
        brains = [
            self._make_brain("News Item", now, score=1.0),
            self._make_brain("Document", now, score=1.0),
        ]

        ranked = rerank_brains(brains, now=now)
        # Document (boost=3.0) should be first
        assert ranked[0][0].portal_type == "Document"
        assert ranked[1][0].portal_type == "News Item"

    def test_decay_affects_ranking(self):
        """Newer content should rank higher when boost is equal."""
        from c2.search.reranker.reranker import rerank_brains

        now = DateTime("2025-06-01 00:00:00 UTC")
        old_date = DateTime("2024-06-01 00:00:00 UTC")  # 365 days ago
        new_date = DateTime("2025-05-30 00:00:00 UTC")  # 2 days ago

        brains = [
            self._make_brain("Document", old_date, score=1.0),
            self._make_brain("Document", new_date, score=1.0),
        ]

        ranked = rerank_brains(brains, now=now)
        # Newer document should be first
        assert ranked[0][0].modified == new_date
        assert ranked[1][0].modified == old_date

    def test_score_details_structure(self):
        """Verify score_details dict has all expected keys."""
        from c2.search.reranker.reranker import rerank_brains

        now = DateTime("2025-06-01 00:00:00 UTC")
        brains = [self._make_brain("Document", now, score=0.8)]

        ranked = rerank_brains(brains, now=now)
        _, details = ranked[0]

        assert "original_score" in details
        assert "boost" in details
        assert "decay" in details
        assert "final_score" in details

    def test_boost_times_decay(self):
        """final_score should equal original_score * boost * decay."""
        from c2.search.reranker.interfaces import IRerankerSettings
        from c2.search.reranker.reranker import rerank_brains
        from plone.registry.interfaces import IRegistry
        from zope.component import getUtility

        registry = getUtility(IRegistry)
        settings = registry.forInterface(IRerankerSettings)
        settings.group_general_content_types = ("Document",)
        settings.group_general_boost = 2.0
        settings.group_general_halflife = 30

        now = DateTime("2025-06-01 00:00:00 UTC")
        modified = DateTime("2025-05-02 00:00:00 UTC")  # 30 days ago
        brains = [self._make_brain("Document", modified, score=0.9)]

        ranked = rerank_brains(brains, now=now)
        _, details = ranked[0]

        expected = 0.9 * 2.0 * 0.5  # score * boost * decay(30days/30halflife)
        assert details["final_score"] == pytest.approx(expected, rel=0.01)

    def test_empty_brains(self):
        """Empty input should return empty list."""
        from c2.search.reranker.reranker import rerank_brains

        now = DateTime()
        assert rerank_brains([], now=now) == []
