"""Built-in rule implementations for Sprint 6.

Each rule is a stateless, deterministic function that returns
zero or more FindingSpecs. Rules never access the database.
"""

from __future__ import annotations

from app.rules.base import BaseRule, FindingSpec, RuleContext

# ── Threshold constants ──────────────────────────────────────────────────

_MIN_UPLOAD_FREQUENCY = 0.02       # ~1 video every 50 days
_MIN_ENGAGEMENT_RATE = 0.01        # 1%
_MAX_SHORTS_RATIO = 0.5            # 50% shorts
_MIN_AVERAGE_VIEWS = 1000          # 1K views per video
_INCONSISTENT_FREQUENCY = 0.01     # ~1 video every 100 days
_NEW_CHANNEL_DAYS = 90             # 3 months


# ── Rules ─────────────────────────────────────────────────────────────────


class LowUploadFrequencyRule(BaseRule):
    """Triggers when upload frequency falls below threshold."""

    @property
    def rule_id(self) -> str:
        return "low_upload_frequency"

    def evaluate(self, context: RuleContext) -> list[FindingSpec]:
        freq = context.feature_vector.features.get("upload_frequency")
        if freq is not None and isinstance(freq, (int, float)) and freq < _MIN_UPLOAD_FREQUENCY:
            return [
                FindingSpec(
                    rule_id=self.rule_id,
                    severity="MEDIUM",
                    category="publishing",
                    title="Low upload frequency",
                    description=(
                        f"Your upload frequency ({freq:.3f} videos/day) "
                        f"is below the recommended threshold of "
                        f"{_MIN_UPLOAD_FREQUENCY} videos/day. "
                        f"Consistent publishing helps maintain audience engagement."
                    ),
                    evidence={
                        "upload_frequency": freq,
                        "threshold": _MIN_UPLOAD_FREQUENCY,
                    },
                )
            ]
        return []


class LowEngagementRateRule(BaseRule):
    """Triggers when engagement rate falls below threshold."""

    @property
    def rule_id(self) -> str:
        return "low_engagement_rate"

    def evaluate(self, context: RuleContext) -> list[FindingSpec]:
        er = context.feature_vector.features.get("engagement_rate")
        if er is not None and isinstance(er, (int, float)) and er < _MIN_ENGAGEMENT_RATE:
            return [
                FindingSpec(
                    rule_id=self.rule_id,
                    severity="HIGH",
                    category="engagement",
                    title="Low engagement rate",
                    description=(
                        f"Your engagement rate ({er:.3f}) is below the "
                        f"recommended threshold of {_MIN_ENGAGEMENT_RATE}. "
                        f"Consider reviewing your content strategy to "
                        f"encourage more likes, comments, and shares."
                    ),
                    evidence={
                        "engagement_rate": er,
                        "threshold": _MIN_ENGAGEMENT_RATE,
                    },
                )
            ]
        return []


class HighShortsRatioRule(BaseRule):
    """Triggers when shorts ratio exceeds threshold."""

    @property
    def rule_id(self) -> str:
        return "high_shorts_ratio"

    def evaluate(self, context: RuleContext) -> list[FindingSpec]:
        sr = context.feature_vector.features.get("shorts_ratio")
        if sr is not None and isinstance(sr, (int, float)) and sr > _MAX_SHORTS_RATIO:
            return [
                FindingSpec(
                    rule_id=self.rule_id,
                    severity="INFO",
                    category="content_format",
                    title="High shorts ratio",
                    description=(
                        f"Shorts make up {sr:.1%} of your uploads. "
                        f"While shorts are great for reach, a balanced "
                        f"mix of long-form content helps build deeper "
                        f"audience connection."
                    ),
                    evidence={
                        "shorts_ratio": sr,
                        "threshold": _MAX_SHORTS_RATIO,
                    },
                )
            ]
        return []


class LowAverageViewsRule(BaseRule):
    """Triggers when average views per video falls below threshold."""

    @property
    def rule_id(self) -> str:
        return "low_average_views"

    def evaluate(self, context: RuleContext) -> list[FindingSpec]:
        avg_views = context.feature_vector.features.get("average_views")
        if avg_views is not None and isinstance(avg_views, (int, float)) and avg_views < _MIN_AVERAGE_VIEWS:
            severity = "MEDIUM" if avg_views >= 500 else "HIGH"
            return [
                FindingSpec(
                    rule_id=self.rule_id,
                    severity=severity,
                    category="performance",
                    title="Low average views",
                    description=(
                        f"Your average views per video ({avg_views:.0f}) "
                        f"are below {_MIN_AVERAGE_VIEWS}. "
                        f"Consider optimizing thumbnails, titles, and "
                        f"video structure to improve reach."
                    ),
                    evidence={
                        "average_views": avg_views,
                        "threshold": _MIN_AVERAGE_VIEWS,
                    },
                )
            ]
        return []


class InconsistentPublishingRule(BaseRule):
    """Triggers when upload frequency is very low, indicating inconsistency."""

    @property
    def rule_id(self) -> str:
        return "inconsistent_publishing"

    def evaluate(self, context: RuleContext) -> list[FindingSpec]:
        freq = context.feature_vector.features.get("upload_frequency")
        if freq is not None and isinstance(freq, (int, float)) and freq < _INCONSISTENT_FREQUENCY:
            return [
                FindingSpec(
                    rule_id=self.rule_id,
                    severity="HIGH",
                    category="publishing",
                    title="Inconsistent publishing schedule",
                    description=(
                        f"Your upload frequency ({freq:.3f} videos/day) "
                        f"indicates large gaps between uploads. "
                        f"Establishing a regular schedule helps retain "
                        f"subscribers and improves algorithmic reach."
                    ),
                    evidence={
                        "upload_frequency": freq,
                        "threshold": _INCONSISTENT_FREQUENCY,
                    },
                )
            ]
        return []


class NewChannelRule(BaseRule):
    """Triggers when the channel is less than NEW_CHANNEL_DAYS old."""

    @property
    def rule_id(self) -> str:
        return "new_channel"

    def evaluate(self, context: RuleContext) -> list[FindingSpec]:
        age = context.feature_vector.features.get("channel_age_days")
        if age is not None and isinstance(age, (int, float)) and age < _NEW_CHANNEL_DAYS:
            return [
                FindingSpec(
                    rule_id=self.rule_id,
                    severity="INFO",
                    category="growth",
                    title="New channel — focus on discovery",
                    description=(
                        f"Your channel is {age:.0f} days old. "
                        f"Focus on discoverability: optimize titles, "
                        f"descriptions, and thumbnails. Experiment with "
                        f"different formats to find your audience."
                    ),
                    evidence={
                        "channel_age_days": age,
                        "threshold": _NEW_CHANNEL_DAYS,
                    },
                )
            ]
        return []
