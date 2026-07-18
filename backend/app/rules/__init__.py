"""Rules module — deterministic rule definitions for the Rule Engine (Sprint 6).

Each rule is a pure function that receives a RuleContext and
returns zero or more Finding objects. Rules are stateless,
independently testable, and never mutate input artifacts.
"""

from app.rules.base import BaseRule, RuleContext
from app.rules.engine import RuleEngine
from app.rules.registry import RuleRegistry
from app.rules.impl import (
    HighShortsRatioRule,
    InconsistentPublishingRule,
    LowAverageViewsRule,
    LowEngagementRateRule,
    LowUploadFrequencyRule,
    NewChannelRule,
)

__all__ = [
    "BaseRule",
    "RuleContext",
    "RuleEngine",
    "RuleRegistry",
    "HighShortsRatioRule",
    "InconsistentPublishingRule",
    "LowAverageViewsRule",
    "LowEngagementRateRule",
    "LowUploadFrequencyRule",
    "NewChannelRule",
]
