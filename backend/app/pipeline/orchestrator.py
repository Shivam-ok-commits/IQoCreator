"""AnalysisPipeline — orchestrates the full analysis pipeline after import.

Runs every stage in order, threading each stage's output as input to the next.
This is the single entry point for triggering a complete analysis cycle.

Pipeline: Import
  → MetricsCollectionStage      (MetricSnapshot)
  → FeatureExtractionStage      (MetricFeatureVector)
  → RuleEngine                  (list[Finding])
  → EvidenceEngine              (list[PipelineEvidence])
  → ClaimEngine                 (list[PipelineClaim])
  → IntelligenceStage           (list[Pattern])
  → RecommendationEngine        (list[PipelineRecommendation])
  → LearningEngine              (list[PipelineExperiment])
  → ReportGenerator             (ExecutiveSummary)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline.claim_engine import ClaimContext, ClaimEngine
from app.pipeline.evidence_engine import EvidenceContext, EvidenceEngine
from app.pipeline.feature_extraction_stage import (
    FeatureExtractionContext,
    FeatureExtractionStage,
)
from app.pipeline.intelligence_stage import (
    IntelligenceContext,
    run_intelligence_stage,
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
from app.pipeline.report_generator import ExecutiveSummary, ReportContext, generate_report, persist_report
from app.repositories.claim_repo import ClaimRepository
from app.repositories.creator_profile_repo import CreatorProfileRepository
from app.repositories.channel_metrics_repo import ChannelMetricsRepository
from app.repositories.experiment_repo import ExperimentRepository
from app.repositories.feature_repo import FeatureRepository
from app.repositories.finding_repo import FindingRepository
from app.repositories.metrics_repo import MetricsRepository
from app.repositories.pipeline_evidence_repo import PipelineEvidenceRepository
from app.repositories.recommendation_repo import RecommendationRepository
from app.repositories.video_repo import VideoRepository
from app.rules import RuleEngine, RuleRegistry
from app.rules.impl import (
    HighShortsRatioRule,
    InconsistentPublishingRule,
    LowAverageViewsRule,
    LowEngagementRateRule,
    LowUploadFrequencyRule,
    NewChannelRule,
)

logger = logging.getLogger(__name__)


@dataclass
class AnalysisPipelineResult:
    snapshot_id: UUID | None = None
    feature_vector_id: UUID | None = None
    finding_count: int = 0
    evidence_count: int = 0
    claim_count: int = 0
    pattern_count: int = 0
    recommendation_count: int = 0
    experiment_count: int = 0
    executive_summary: ExecutiveSummary | None = None


async def run_analysis_pipeline(
    db: AsyncSession,
    creator_profile_id: UUID,
    source_import_run_id: UUID | None = None,
) -> AnalysisPipelineResult:
    """Execute the full analysis pipeline for a given creator profile.

    Each stage consumes the previous stage's output.  If any stage
    produces no output, downstream stages receive empty input and
    produce empty output (no cascade failure).
    """
    result = AnalysisPipelineResult()

    # ── Build rule registry ───────────────────────────────────────────
    registry = RuleRegistry()
    for rule_cls in (
        LowUploadFrequencyRule,
        LowEngagementRateRule,
        HighShortsRatioRule,
        LowAverageViewsRule,
        InconsistentPublishingRule,
        NewChannelRule,
    ):
        registry.register(rule_cls())

    # ── Repositories (shared across stages) ──────────────────────────
    profile_repo = CreatorProfileRepository(db)
    channel_metrics_repo = ChannelMetricsRepository(db)
    video_repo = VideoRepository(db)
    metrics_repo = MetricsRepository(db)
    feature_repo = FeatureRepository(db)
    finding_repo = FindingRepository(db)
    evidence_repo = PipelineEvidenceRepository(db)
    claim_repo = ClaimRepository(db)
    rec_repo = RecommendationRepository(db)
    exp_repo = ExperimentRepository(db)

    # ── Stage 1: MetricsCollectionStage → MetricSnapshot ────────────
    metrics_stage = MetricsCollectionStage(
        creator_profile_repo=profile_repo,
        channel_metrics_repo=channel_metrics_repo,
        video_repo=video_repo,
        metrics_repo=metrics_repo,
    )
    metrics_ctx = MetricsContext(creator_profile_id=creator_profile_id)
    snapshot = await metrics_stage.execute(
        metrics_ctx,
        source_import_run_id=source_import_run_id,
    )
    result.snapshot_id = snapshot.id
    logger.info("Stage 1/7 complete: MetricSnapshot %s", snapshot.id)

    # ── Stage 2: FeatureExtractionStage → MetricFeatureVector ──────
    feature_stage = FeatureExtractionStage(
        metrics_repo=metrics_repo,
        creator_profile_repo=profile_repo,
        video_repo=video_repo,
        feature_repo=feature_repo,
    )
    feat_ctx = FeatureExtractionContext(snapshot_id=snapshot.id)
    feature_vector = await feature_stage.execute(feat_ctx)
    result.feature_vector_id = feature_vector.id
    logger.info("Stage 2/7 complete: MetricFeatureVector %s", feature_vector.id)

    # ── Stage 3: RuleEngine → list[Finding] ─────────────────────────
    rule_engine = RuleEngine(
        finding_repo=finding_repo,
        registry=registry,
    )
    from app.rules.base import RuleContext
    rule_ctx = RuleContext(
        feature_vector=feature_vector,
        creator_profile_id=creator_profile_id,
    )
    findings = await rule_engine.execute(rule_ctx)
    result.finding_count = len(findings)
    logger.info("Stage 3/7 complete: %d Finding(s)", len(findings))

    # ── Stage 4: EvidenceEngine → list[PipelineEvidence] ────────────
    evidence_engine = EvidenceEngine(
        finding_repo=finding_repo,
        evidence_repo=evidence_repo,
    )
    ev_ctx = EvidenceContext(
        findings=tuple(findings),
        feature_vector=feature_vector,
    )
    evidence_list = await evidence_engine.execute(ev_ctx)
    result.evidence_count = len(evidence_list)
    logger.info("Stage 4/7 complete: %d PipelineEvidence", len(evidence_list))

    # ── Stage 5: ClaimEngine → list[PipelineClaim] ──────────────────
    claim_engine = ClaimEngine(claim_repo=claim_repo)
    cl_ctx = ClaimContext(evidence_list=tuple(evidence_list))
    claims = await claim_engine.execute(cl_ctx)
    result.claim_count = len(claims)
    logger.info("Stage 5/8 complete: %d PipelineClaim(s)", len(claims))

    # ── Stage 6: IntelligenceStage → list[Pattern] ─────────────────
    intel_ctx = IntelligenceContext(
        creator_profile_id=creator_profile_id,
        claims=tuple(claims),
    )
    patterns = await run_intelligence_stage(intel_ctx, db)
    result.pattern_count = len(patterns)
    logger.info("Stage 6/8 complete: %d Pattern(s)", len(patterns))

    # ── Stage 7: RecommendationEngine → list[PipelineRecommendation] ─
    rec_engine = RecommendationEngine(recommendation_repo=rec_repo)
    rec_ctx = RecommendationContext(
        claims=tuple(claims),
        patterns=tuple(patterns),
    )
    recs = await rec_engine.execute(rec_ctx)
    result.recommendation_count = len(recs)
    logger.info("Stage 7/8 complete: %d PipelineRecommendation(s)", len(recs))

    # ── Stage 8: LearningEngine → list[PipelineExperiment] ──────────
    learn_engine = LearningEngine(experiment_repo=exp_repo)
    learn_ctx = LearningContext(recommendations=tuple(recs))
    experiments = await learn_engine.execute(learn_ctx)
    result.experiment_count = len(experiments)
    logger.info("Stage 8/9 complete: %d PipelineExperiment(s)", len(experiments))

    # ── Stage 9: ReportGenerator → ExecutiveSummary ─────────────────
    report_ctx = ReportContext(
        creator_profile_id=creator_profile_id,
        analysis_run_id=snapshot.analysis_run_id if hasattr(snapshot, "analysis_run_id") else None,
        patterns=tuple(patterns),
        recommendations=tuple(recs),
    )
    summary = await generate_report(report_ctx, db)
    if summary:
        await persist_report(summary, report_ctx, db)
        result.executive_summary = summary
        logger.info("Stage 9/9 complete: ExecutiveSummary generated")
    else:
        logger.info("Stage 9/9 skipped: insufficient data for report")

    return result
