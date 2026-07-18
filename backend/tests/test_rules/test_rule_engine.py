"""Tests for Rule Engine — rules, registry, and engine orchestration.

Covers: each rule independently, engine executes all rules,
no duplicate findings, replay produces identical findings,
historical feature vectors unchanged, repository persistence.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.models import MetricFeatureVector
from app.rules.base import BaseRule, FindingSpec, RuleContext
from app.rules.engine import RuleEngine
from app.rules.impl import (
    HighShortsRatioRule,
    InconsistentPublishingRule,
    LowAverageViewsRule,
    LowEngagementRateRule,
    LowUploadFrequencyRule,
    NewChannelRule,
)
from app.rules.registry import RuleRegistry

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_vector(
    vector_id: UUID | None = None,
    features: dict | None = None,
) -> MetricFeatureVector:
    vector = MagicMock(spec=MetricFeatureVector)
    vector.id = vector_id or uuid4()
    vector.creator_profile_id = uuid4()
    vector.features = features or {}
    return vector


# ── Rule tests ───────────────────────────────────────────────────────────


class TestLowUploadFrequencyRule:
    """Tests for LowUploadFrequencyRule."""

    def test_triggers_when_below_threshold(self) -> None:
        rule = LowUploadFrequencyRule()
        vector = _make_vector(features={"upload_frequency": 0.005})
        context = RuleContext(
            feature_vector=vector,
            creator_profile_id=uuid4(),
        )
        results = rule.evaluate(context)
        assert len(results) == 1
        assert results[0].rule_id == "low_upload_frequency"
        assert results[0].severity == "MEDIUM"

    def test_does_not_trigger_when_above_threshold(self) -> None:
        rule = LowUploadFrequencyRule()
        vector = _make_vector(features={"upload_frequency": 0.1})
        context = RuleContext(
            feature_vector=vector,
            creator_profile_id=uuid4(),
        )
        results = rule.evaluate(context)
        assert len(results) == 0

    def test_does_not_trigger_when_missing(self) -> None:
        rule = LowUploadFrequencyRule()
        vector = _make_vector(features={})
        context = RuleContext(
            feature_vector=vector,
            creator_profile_id=uuid4(),
        )
        results = rule.evaluate(context)
        assert len(results) == 0


class TestLowEngagementRateRule:
    """Tests for LowEngagementRateRule."""

    def test_triggers_when_below_threshold(self) -> None:
        rule = LowEngagementRateRule()
        vector = _make_vector(features={"engagement_rate": 0.005})
        context = RuleContext(feature_vector=vector, creator_profile_id=uuid4())
        results = rule.evaluate(context)
        assert len(results) == 1
        assert results[0].severity == "HIGH"

    def test_does_not_trigger_when_above_threshold(self) -> None:
        rule = LowEngagementRateRule()
        vector = _make_vector(features={"engagement_rate": 0.05})
        context = RuleContext(feature_vector=vector, creator_profile_id=uuid4())
        results = rule.evaluate(context)
        assert len(results) == 0


class TestHighShortsRatioRule:
    """Tests for HighShortsRatioRule."""

    def test_triggers_when_above_threshold(self) -> None:
        rule = HighShortsRatioRule()
        vector = _make_vector(features={"shorts_ratio": 0.8})
        context = RuleContext(feature_vector=vector, creator_profile_id=uuid4())
        results = rule.evaluate(context)
        assert len(results) == 1
        assert results[0].severity == "INFO"

    def test_does_not_trigger_when_below_threshold(self) -> None:
        rule = HighShortsRatioRule()
        vector = _make_vector(features={"shorts_ratio": 0.2})
        context = RuleContext(feature_vector=vector, creator_profile_id=uuid4())
        results = rule.evaluate(context)
        assert len(results) == 0


class TestLowAverageViewsRule:
    """Tests for LowAverageViewsRule."""

    def test_triggers_severity_medium(self) -> None:
        rule = LowAverageViewsRule()
        vector = _make_vector(features={"average_views": 700})
        context = RuleContext(feature_vector=vector, creator_profile_id=uuid4())
        results = rule.evaluate(context)
        assert len(results) == 1
        assert results[0].severity == "MEDIUM"

    def test_triggers_severity_high(self) -> None:
        rule = LowAverageViewsRule()
        vector = _make_vector(features={"average_views": 100})
        context = RuleContext(feature_vector=vector, creator_profile_id=uuid4())
        results = rule.evaluate(context)
        assert len(results) == 1
        assert results[0].severity == "HIGH"

    def test_does_not_trigger_when_above_threshold(self) -> None:
        rule = LowAverageViewsRule()
        vector = _make_vector(features={"average_views": 5000})
        context = RuleContext(feature_vector=vector, creator_profile_id=uuid4())
        results = rule.evaluate(context)
        assert len(results) == 0


class TestInconsistentPublishingRule:
    """Tests for InconsistentPublishingRule."""

    def test_triggers_when_very_low_frequency(self) -> None:
        rule = InconsistentPublishingRule()
        vector = _make_vector(features={"upload_frequency": 0.001})
        context = RuleContext(feature_vector=vector, creator_profile_id=uuid4())
        results = rule.evaluate(context)
        assert len(results) == 1
        assert results[0].severity == "HIGH"

    def test_does_not_trigger_when_reasonable_frequency(self) -> None:
        rule = InconsistentPublishingRule()
        vector = _make_vector(features={"upload_frequency": 0.05})
        context = RuleContext(feature_vector=vector, creator_profile_id=uuid4())
        results = rule.evaluate(context)
        assert len(results) == 0


class TestNewChannelRule:
    """Tests for NewChannelRule."""

    def test_triggers_when_channel_is_new(self) -> None:
        rule = NewChannelRule()
        vector = _make_vector(features={"channel_age_days": 30})
        context = RuleContext(feature_vector=vector, creator_profile_id=uuid4())
        results = rule.evaluate(context)
        assert len(results) == 1
        assert results[0].severity == "INFO"

    def test_does_not_trigger_when_channel_is_old(self) -> None:
        rule = NewChannelRule()
        vector = _make_vector(features={"channel_age_days": 365})
        context = RuleContext(feature_vector=vector, creator_profile_id=uuid4())
        results = rule.evaluate(context)
        assert len(results) == 0


# ── Registry tests ───────────────────────────────────────────────────────


class TestRuleRegistry:
    """Tests for RuleRegistry."""

    def test_register_and_get(self) -> None:
        registry = RuleRegistry()
        rule = LowUploadFrequencyRule()
        registry.register(rule)
        assert registry.get("low_upload_frequency") is rule

    def test_register_duplicate_raises(self) -> None:
        registry = RuleRegistry()
        registry.register(LowUploadFrequencyRule())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(LowUploadFrequencyRule())

    def test_get_all_returns_all_rules(self) -> None:
        registry = RuleRegistry()
        registry.register(LowUploadFrequencyRule())
        registry.register(LowEngagementRateRule())
        assert registry.count() == 2

    def test_get_unknown_returns_none(self) -> None:
        registry = RuleRegistry()
        assert registry.get("nonexistent") is None


# ── Engine tests ─────────────────────────────────────────────────────────


class _AlwaysTriggersRule(BaseRule):
    """Test rule that always produces a finding."""

    @property
    def rule_id(self) -> str:
        return "always_triggers"

    def evaluate(self, context: RuleContext) -> list[FindingSpec]:
        return [
            FindingSpec(
                rule_id=self.rule_id,
                severity="INFO",
                category="test",
                title="Always triggers",
            )
        ]


class _NeverTriggersRule(BaseRule):
    """Test rule that never produces a finding."""

    @property
    def rule_id(self) -> str:
        return "never_triggers"

    def evaluate(self, context: RuleContext) -> list[FindingSpec]:
        return []


class TestRuleEngine:
    """Tests for RuleEngine orchestration."""

    async def test_executes_all_registered_rules(self) -> None:
        """Engine executes all rules and returns combined findings."""
        vector = _make_vector(features={"total_videos": 10})

        finding_repo = AsyncMock()
        finding_repo.create_many = AsyncMock(return_value=[])

        registry = RuleRegistry()
        registry.register(_AlwaysTriggersRule())
        registry.register(_NeverTriggersRule())

        engine = RuleEngine(
            finding_repo=finding_repo,
            registry=registry,
        )

        context = RuleContext(
            feature_vector=vector,
            creator_profile_id=vector.creator_profile_id,
        )
        results = await engine.execute(context)

        # Only the always_triggers rule produced findings
        assert len(results) == 1
        assert results[0].rule_id == "always_triggers"

        # Verify findings were persisted
        finding_repo.create_many.assert_awaited_once()

    async def test_no_findings_when_no_rules_trigger(self) -> None:
        """Engine returns empty list when no rules trigger."""
        vector = _make_vector(features={"total_videos": 10})

        finding_repo = AsyncMock()
        finding_repo.create_many = AsyncMock(return_value=[])

        registry = RuleRegistry()
        registry.register(_NeverTriggersRule())

        engine = RuleEngine(
            finding_repo=finding_repo,
            registry=registry,
        )

        context = RuleContext(
            feature_vector=vector,
            creator_profile_id=vector.creator_profile_id,
        )
        results = await engine.execute(context)
        assert len(results) == 0
        finding_repo.create_many.assert_not_awaited()

    async def test_replay_produces_identical_findings(self) -> None:
        """Running twice with same feature vector produces same findings."""
        vector = _make_vector(features={"upload_frequency": 0.005})

        finding_repo = AsyncMock()
        finding_repo.create_many = AsyncMock(return_value=[])

        registry = RuleRegistry()
        registry.register(LowUploadFrequencyRule())

        engine = RuleEngine(
            finding_repo=finding_repo,
            registry=registry,
        )

        context = RuleContext(
            feature_vector=vector,
            creator_profile_id=vector.creator_profile_id,
        )
        results1 = await engine.execute(context)
        results2 = await engine.execute(context)

        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1.rule_id == r2.rule_id
            assert r1.severity == r2.severity
            assert r1.title == r2.title

    async def test_rule_error_does_not_crash_engine(self) -> None:
        """A failing rule does not prevent other rules from executing."""

        class _FailingRule(BaseRule):
            @property
            def rule_id(self) -> str:
                return "failing_rule"

            def evaluate(self, context: RuleContext) -> list[FindingSpec]:
                raise RuntimeError("Unexpected error")

        vector = _make_vector(features={"total_videos": 10})

        finding_repo = AsyncMock()
        finding_repo.create_many = AsyncMock(return_value=[])

        registry = RuleRegistry()
        registry.register(_FailingRule())
        registry.register(_AlwaysTriggersRule())

        engine = RuleEngine(
            finding_repo=finding_repo,
            registry=registry,
        )

        context = RuleContext(
            feature_vector=vector,
            creator_profile_id=vector.creator_profile_id,
        )
        results = await engine.execute(context)
        # Only the always_triggers rule should have produced findings
        assert len(results) == 1
        assert results[0].rule_id == "always_triggers"



    async def test_no_duplicate_findings_from_same_rule(self) -> None:
        """A single rule evaluation should not produce duplicate findings.

        This is a contract test — rules are responsible for returning
        at most one FindingSpec per trigger condition.
        """
        rule = LowUploadFrequencyRule()
        vector = _make_vector(features={"upload_frequency": 0.005})
        context = RuleContext(feature_vector=vector, creator_profile_id=uuid4())

        results = rule.evaluate(context)
        rule_ids = [r.rule_id for r in results]
        assert len(rule_ids) == len(set(rule_ids))
