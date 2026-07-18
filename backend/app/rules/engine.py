"""RuleEngine — orchestrates rule evaluation against a FeatureVector.

Consumes a pre-built RuleContext, evaluates all registered rules,
and persists the resulting Finding artifacts.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from app.models import Finding
from app.repositories.finding_repo import FindingRepository
from app.rules.base import FindingSpec, RuleContext
from app.rules.registry import RuleRegistry

logger = logging.getLogger(__name__)


class RuleEngine:
    """Orchestrates rule evaluation for a single RuleContext.

    Responsibilities
    -----------------
    1. Execute all registered rules against the context.
    2. Persist the resulting Findings.

    Non-responsibilities
    ---------------------
    - Does not load FeatureVectors (caller provides context).
    - Does not implement rule logic (delegates to BaseRule implementations).
    - Does not mutate any input artifact.
    - Does not produce recommendations or evidence.
    """

    def __init__(
        self,
        *,
        finding_repo: FindingRepository,
        registry: RuleRegistry,
    ) -> None:
        self._finding_repo = finding_repo
        self._registry = registry

    async def execute(
        self,
        context: RuleContext,
    ) -> list[Finding]:
        """Execute all registered rules against a RuleContext.

        Parameters
        ----------
        context : RuleContext
            Pre-built context containing the FeatureVector and creator ID.

        Returns
        -------
        list[Finding]
            All findings produced by this execution run.
        """
        vector = context.feature_vector
        feature_vector_id = vector.id

        # ── 1. Execute all rules ─────────────────────────────────────
        all_specs: list[FindingSpec] = []
        for rule in self._registry.get_all():
            try:
                specs = rule.evaluate(context)
                all_specs.extend(specs)
            except Exception:
                logger.exception(
                    "Rule '%s' failed for feature vector %s",
                    rule.rule_id, feature_vector_id,
                )

        # ── 2. Persist findings ──────────────────────────────────────
        found_severities: dict[str, int] = {}
        findings: list[Finding] = []

        for spec in all_specs:
            finding = Finding(
                id=uuid4(),
                creator_profile_id=vector.creator_profile_id,
                source_feature_vector_id=feature_vector_id,
                rule_id=spec.rule_id,
                severity=spec.severity,
                category=spec.category,
                title=spec.title,
                description=spec.description,
                evidence=spec.evidence,
            )
            findings.append(finding)
            found_severities[spec.severity] = (
                found_severities.get(spec.severity, 0) + 1
            )

        if findings:
            await self._finding_repo.create_many(findings)
            logger.info(
                "RuleEngine created %d findings for feature vector %s "
                "(severities: %s)",
                len(findings), feature_vector_id, found_severities,
            )
        else:
            logger.info(
                "RuleEngine: no findings for feature vector %s",
                feature_vector_id,
            )

        return findings
