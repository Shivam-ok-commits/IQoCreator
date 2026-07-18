"""Pipeline module — intelligence pipeline stages for Sprints 5-10.

Each stage consumes one immutable artifact and produces the next.
Stages are deterministic, independently testable, and idempotent.
Complete pipeline: Import → MetricSnapshot → FeatureVector →
Finding → Evidence → Claim → Recommendation → Experiment.
"""

from app.pipeline.claim_engine import ClaimContext, ClaimEngine
from app.pipeline.evidence_engine import EvidenceContext, EvidenceEngine
from app.pipeline.feature_extraction_stage import (
    FeatureExtractionContext,
    FeatureExtractionStage,
)
from app.pipeline.learning_engine import LearningContext, LearningEngine
from app.pipeline.metrics_collection_stage import (
    MetricsCollectionStage,
    MetricsContext,
)
from app.pipeline.recommendation_engine import (
    RecommendationContext,
    RecommendationEngine,
)
from app.pipeline.triggers import (
    ImportTriggerService,
    TriggerRequest,
    TriggerResult,
    TriggerType,
)

__all__ = [
    "ClaimContext",
    "ClaimEngine",
    "EvidenceContext",
    "EvidenceEngine",
    "FeatureExtractionContext",
    "FeatureExtractionStage",
    "LearningContext",
    "LearningEngine",
    "MetricsCollectionStage",
    "MetricsContext",
    "RecommendationContext",
    "RecommendationEngine",
    "ImportTriggerService",
    "TriggerRequest",
    "TriggerResult",
    "TriggerType",
]
