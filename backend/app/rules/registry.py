"""RuleRegistry — central registry for rule discovery and registration."""

from __future__ import annotations

from app.rules.base import BaseRule


class RuleRegistry:
    """Registry of all available rules.

    Rules register themselves here. The RuleEngine queries the
    registry to discover which rules to execute.

    Singleton-free — instantiate once and share via dependency injection.
    """

    def __init__(self) -> None:
        self._rules: dict[str, BaseRule] = {}

    def register(self, rule: BaseRule) -> None:
        """Register a rule instance.

        Raises ValueError if a rule with the same rule_id is
        already registered.
        """
        if rule.rule_id in self._rules:
            raise ValueError(f"Rule '{rule.rule_id}' is already registered")
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> BaseRule | None:
        """Get a rule by its rule_id."""
        return self._rules.get(rule_id)

    def get_all(self) -> list[BaseRule]:
        """Get all registered rules."""
        return list(self._rules.values())

    def count(self) -> int:
        """Return the number of registered rules."""
        return len(self._rules)
