"""Models module — SQLAlchemy ORM models.

All models are imported here so Alembic autogenerate detects them.
One file per model for maintainability.
"""

from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.models.creator_profile import CreatorProfile
from app.models.channel_metrics import ChannelMetrics
from app.models.video import Video
from app.models.video_metrics import VideoMetrics
from app.models.feature_vector import FeatureVector
from app.models.import_run import ImportRun, ImportRunStatus
from app.models.metric_feature_vector import MetricFeatureVector
from app.models.metric_snapshot import MetricSnapshot
from app.models.analysis_run import AnalysisRun, AnalysisRunStatus
from app.models.rule_execution import RuleExecution, RuleExecutionStatus
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.pipeline_claim import PipelineClaim
from app.models.pipeline_evidence import PipelineEvidence
from app.models.pipeline_experiment import PipelineExperiment
from app.models.pipeline_recommendation import PipelineRecommendation
from app.models.claim_evidence import ClaimEvidence
from app.models.claim import Claim, ClaimStatus
from app.models.recommendation import Recommendation, RecommendationStatus
from app.models.recommendation_feedback import RecommendationFeedback
from app.models.experiment import Experiment, ExperimentStatus
from app.models.experiment_result import ExperimentResult
from app.models.growth_score import GrowthScore
from app.models.pipeline_pattern import PipelinePattern
from app.models.channel_report import ChannelReport

__all__ = [
    "User",
    "ConnectedAccount",
    "CreatorProfile",
    "ChannelMetrics",
    "Video",
    "VideoMetrics",
    "FeatureVector",
    "MetricFeatureVector",
    "MetricSnapshot",
    "ImportRun",
    "ImportRunStatus",
    "AnalysisRun",
    "AnalysisRunStatus",
    "RuleExecution",
    "RuleExecutionStatus",
    "Finding",
    "PipelineClaim",
    "PipelineEvidence",
    "PipelineExperiment",
    "PipelineRecommendation",
    "Evidence",
    "ClaimEvidence",
    "Claim",
    "ClaimStatus",
    "Recommendation",
    "RecommendationStatus",
    "RecommendationFeedback",
    "Experiment",
    "ExperimentStatus",
    "ExperimentResult",
    "GrowthScore",
    "PipelinePattern",
    "ChannelReport",
]
