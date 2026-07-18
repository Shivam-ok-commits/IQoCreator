"""Base rule abstraction and execution context for the Rule Engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from app.models import MetricFeatureVector


@dataclass(frozen=True)
class RuleContext:
    """Immutable context passed to every rule for evaluation.

    Contains the feature vector and creator identifiers.
    Rules must not mutate this context.
    """

    feature_vector: MetricFeatureVector
    creator_profile_id: UUID


@dataclass(frozen=True)
class FindingSpec:
    """Specification for a Finding to be created by a rule.

    Immutable — used by RuleEngine to construct the Finding model.
    """

    rule_id: str
    severity: str  # INFO, LOW, MEDIUM, HIGH
    category: str
    title: str
    description: str | None = None
    evidence: dict | None = None


class BaseRule(ABC):
    """Abstract base class for all rules.

    Rules are pure functions that evaluate a RuleContext and return
    zero or more FindingSpecs. Rules never access the database,
    never mutate input artifacts, and never have side effects.

    Subclasses must implement:
    - rule_id: str — unique identifier
    - evaluate(context: RuleContext) -> list[FindingSpec]
    """

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique identifier for this rule (e.g. 'low_upload_frequency')."""

    @abstractmethod
    def evaluate(self, context: RuleContext) -> list[FindingSpec]:
        """Evaluate this rule against the given context.

        Returns zero or more FindingSpecs. Empty list means
        the rule did not trigger.
        """
