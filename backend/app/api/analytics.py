"""Analytics API — pipeline data endpoints.

Provides authenticated read-only access to the pipeline artifact tables
(MetricSnapshot, FeatureVector, Findings, Evidence, Claims,
Recommendations, Experiments) so the frontend Analytics page can
display real backend data without mock data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum as PyEnum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import joinedload

from app.database.session import get_db
from app.models import (
    ChannelMetrics,
    ChannelReport,
    ConnectedAccount,
    CreatorProfile,
    Finding,
    GrowthScore,
    MetricSnapshot,
    MetricFeatureVector,
    PipelineClaim,
    PipelineEvidence,
    PipelineExperiment,
    PipelinePattern,
    PipelineRecommendation,
    Video,
    VideoMetrics,
)
from app.repositories.finding_repo import FindingRepository
from app.services.session import get_session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# ═══════════════════════════════════════════════════════════════════════════
# Domain objects — typed, serializable, shared across surfaces
# ═══════════════════════════════════════════════════════════════════════════


class MissionVerdict(str, PyEnum):
    """Stable semantic outcome for a completed (or in-progress) mission.

    The API renders human-readable text, but downstream consumers
    (notifications, emails, history) can switch on the enum value.
    """

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    INCONCLUSIVE = "inconclusive"
    UNSUCCESSFUL = "unsuccessful"
    IN_PROGRESS = "in_progress"
    NOT_STARTED = "not_started"


VERDICT_LABELS: dict[MissionVerdict, str] = {
    MissionVerdict.SUCCESS: "Mission successful — the data confirms the strategy is working.",
    MissionVerdict.PARTIAL_SUCCESS: "Mission on track — progress is visible.",
    MissionVerdict.INCONCLUSIVE: "Mission completed, but results are mixed.",
    MissionVerdict.UNSUCCESSFUL: "Mission completed, but results suggest the approach needs adjustment.",
    MissionVerdict.IN_PROGRESS: "Still in progress — we'll measure the outcome next review.",
    MissionVerdict.NOT_STARTED: "Not yet started — consider beginning this week to accelerate growth.",
}


@dataclass
class EvidenceItem:
    """A single data point supporting the review's conclusion."""
    label: str
    detail: str
    pct_change: float | None = None
    category: str = "other"
    severity: str = "info"


@dataclass
class MissionOutcome:
    """Numerical outcome for a mission's primary metric."""
    metric: str
    before: float
    after: float
    change_pct: float


@dataclass
class LastMission:
    """The mission from the previous review, its outcome, and a verdict."""
    description: str
    status: str  # "completed" | "in_progress" | "not_started"
    outcome: MissionOutcome | None = None
    verdict: str = ""
    verdict_enum: str = "not_started"


@dataclass
class GrowthReview:
    """A compute-on-read consultation answering "Did following our advice help?"

    NOT a database model.  This is a typed domain object that the endpoint
    constructs and serialises.  Every surface — dashboard, email, notifications,
    PDF export, AI chat — should consume the exact same GrowthReview object.

    The 5-act conversation:
      1. review        — executive assessment (conclusion)
      2. evidence      — strengths + concerns (why)
      3. last_mission  — what we asked, what happened, verdict
      4. new_questions — what we still don't know
      5. next_focus    — what to do next
    """

    has_review: bool = True
    has_history: bool = False
    review: str = ""
    evidence_strengths: list[EvidenceItem] = field(default_factory=list)
    evidence_concerns: list[EvidenceItem] = field(default_factory=list)
    last_mission: LastMission | None = None
    new_questions: list[str] = field(default_factory=list)
    next_focus: str = ""

    def to_dict(self) -> dict:
        """Serialise to the API response shape."""
        return {
            "has_review": self.has_review,
            "has_history": self.has_history,
            "review": self.review,
            "evidence": {
                "strengths": [
                    {"label": s.label, "detail": s.detail,
                     "pct_change": s.pct_change, "category": s.category}
                    for s in self.evidence_strengths
                ],
                "concerns": [
                    {"label": c.label, "detail": c.detail,
                     "pct_change": c.pct_change, "category": c.category,
                     "severity": c.severity}
                    for c in self.evidence_concerns
                ],
            },
            "last_mission": None if not self.last_mission else {
                "description": self.last_mission.description,
                "status": self.last_mission.status,
                "outcome": None if not self.last_mission.outcome else {
                    "metric": self.last_mission.outcome.metric,
                    "before": self.last_mission.outcome.before,
                    "after": self.last_mission.outcome.after,
                    "change_pct": self.last_mission.outcome.change_pct,
                },
                "verdict": self.last_mission.verdict,
                "verdict_enum": self.last_mission.verdict_enum,
            },
            "new_questions": self.new_questions,
            "next_focus": self.next_focus,
        }


# ── Helpers ────────────────────────────────────────────────────────────────


def _format_delta(
    current: float | int | None,
    previous: float | int | None,
) -> tuple[float | None, float | None]:
    """Compute absolute delta and percentage change."""
    if current is None or previous is None or previous == 0:
        return None, None
    delta = current - previous
    pct = (delta / previous) * 100
    return delta, pct


def _describe_pct(pct: float | None) -> str:
    """Format a percentage change as a human-friendly label."""
    if pct is None:
        return ""
    if pct > 50:
        return "increased significantly"
    if pct > 15:
        return "increased"
    if pct > 3:
        return "slightly increased"
    if pct > -3:
        return "remained stable"
    if pct > -15:
        return "slightly declined"
    if pct > -50:
        return "declined"
    return "declined significantly"


async def _resolve_creator(
    request: Request, db: AsyncSession
) -> tuple[CreatorProfile, ConnectedAccount]:
    """Verify session and return the user's creator profile + account."""
    sess = get_session_service()
    user_id = sess.verify_cookie(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session")

    result = await db.execute(
        select(CreatorProfile).where(
            CreatorProfile.user_id == uid,
            CreatorProfile.platform == "youtube",
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="No creator profile found")

    result2 = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == uid,
            ConnectedAccount.provider == "google",
        )
    )
    account = result2.scalar_one_or_none()

    return profile, account


@router.get("/summary")
async def analytics_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return a summary of all pipeline artifacts for the authenticated user."""
    profile, _ = await _resolve_creator(request, db)

    # Latest metrics
    metrics_result = await db.execute(
        select(ChannelMetrics)
        .where(ChannelMetrics.creator_profile_id == profile.id)
        .order_by(desc(ChannelMetrics.recorded_at))
        .limit(1)
    )
    latest_metrics = metrics_result.scalar_one_or_none()

    # Latest MetricSnapshot
    snap_result = await db.execute(
        select(MetricSnapshot)
        .where(MetricSnapshot.creator_profile_id == profile.id)
        .order_by(desc(MetricSnapshot.snapshot_at))
        .limit(1)
    )
    latest_snapshot = snap_result.scalar_one_or_none()

    # Latest FeatureVector
    fv_result = await db.execute(
        select(MetricFeatureVector)
        .where(MetricFeatureVector.creator_profile_id == profile.id)
        .order_by(desc(MetricFeatureVector.computed_at))
        .limit(1)
    )
    latest_feature_vector = fv_result.scalar_one_or_none()

    # Findings (severity is a plain Mapped[str], stored uppercase)
    finding_repo = FindingRepository(db)
    all_findings = await finding_repo.get_by_creator(profile.id)
    high_findings = [f for f in all_findings if f.severity == "HIGH"]
    critical_findings = [f for f in all_findings if f.severity == "CRITICAL"]

    return {
        "channel_metrics": {
            "subscriber_count": latest_metrics.subscriber_count
            if latest_metrics
            else None,
            "total_views": latest_metrics.total_views if latest_metrics else None,
            "total_videos": latest_metrics.total_videos if latest_metrics else None,
        },
        "metric_snapshot": {
            "snapshot_at": latest_snapshot.snapshot_at.isoformat()
            if latest_snapshot
            else None,
            "total_videos": latest_snapshot.total_videos if latest_snapshot else None,
            "total_views": latest_snapshot.total_views if latest_snapshot else None,
            "total_subscribers": latest_snapshot.total_subscribers
            if latest_snapshot
            else None,
            "engagement_rate": latest_snapshot.engagement_rate
            if latest_snapshot
            else None,
        }
        if latest_snapshot
        else None,
        "feature_vector": {
            "computed_at": latest_feature_vector.computed_at.isoformat()
            if latest_feature_vector
            else None,
            "features": latest_feature_vector.features
            if latest_feature_vector
            else {},
            "schema_version": latest_feature_vector.feature_schema_version
            if latest_feature_vector
            else None,
        }
        if latest_feature_vector
        else None,
        "findings": {
            "total": len(all_findings),
            "high_severity": len(high_findings),
            "critical_severity": len(critical_findings),
            "items": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "category": f.category,
                    "title": f.title,
                    "description": f.description,
                }
                for f in all_findings[:10]
            ],
        },
    }


@router.get("/review")
async def growth_review(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Growth Review — compute-on-read consultation answering:

    *"Did following our advice help?"*
    not *"Did your metrics change?"*.

    The response is structured as a 5-act conversation rather than a
    dashboard of sections:

    1. Here's what happened   (executive conclusion)
    2. Here's why             (evidence: strengths + concerns)
    3. Did our advice work?   (last week's mission + outcome + verdict)
    4. What we still don't know  (new questions → next experiment)
    5. What to do next           (next focus)
    """
    profile, _ = await _resolve_creator(request, db)
    pid = profile.id

    # ── 1. Growth Scores (current + previous) ─────────────────────────
    gs_result = await db.execute(
        select(GrowthScore)
        .where(GrowthScore.creator_profile_id == pid)
        .order_by(desc(GrowthScore.recorded_at))
        .limit(2)
    )
    gs_scores = gs_result.scalars().all()

    # ── 2. Metric Snapshots (current + previous) ──────────────────────
    snap_result = await db.execute(
        select(MetricSnapshot)
        .where(MetricSnapshot.creator_profile_id == pid)
        .order_by(desc(MetricSnapshot.snapshot_at))
        .limit(2)
    )
    snapshots = snap_result.scalars().all()

    # ── 3. Channel Reports (latest two) ───────────────────────────────
    report_result = await db.execute(
        select(ChannelReport)
        .where(ChannelReport.creator_profile_id == pid)
        .order_by(desc(ChannelReport.recorded_at))
        .limit(2)
    )
    reports = report_result.scalars().all()

    # ── 4. Experiments ────────────────────────────────────────────────
    exp_result = await db.execute(
        select(PipelineExperiment)
        .where(PipelineExperiment.creator_profile_id == pid)
        .order_by(desc(PipelineExperiment.created_at))
    )
    all_experiments = exp_result.scalars().all()

    # ── 5. Findings (current risks) ───────────────────────────────────
    finding_repo = FindingRepository(db)
    findings = await finding_repo.get_by_creator(pid)

    # ── 6. Patterns (for open questions) ──────────────────────────────
    pat_result = await db.execute(
        select(PipelinePattern)
        .where(PipelinePattern.creator_profile_id == pid)
        .order_by(PipelinePattern.impact_score.desc())
    )
    patterns = pat_result.scalars().all()

    # ── Derive review data ────────────────────────────────────────────

    gs_current = gs_scores[0] if gs_scores else None
    gs_previous = gs_scores[1] if len(gs_scores) > 1 else None
    snap_current = snapshots[0] if snapshots else None
    snap_previous = snapshots[1] if len(snapshots) > 1 else None
    report_latest = reports[0] if reports else None
    report_previous = reports[1] if len(reports) > 1 else None

    # ── Can we build a review? ────────────────────────────────────────
    has_review = (
        gs_current is not None
        or snap_current is not None
        or len(all_experiments) > 0
    )
    if not has_review:
        return {"has_review": False, "message": "No analysis data yet. Run an analysis to generate a Growth Review."}

    has_history = gs_previous is not None or snap_previous is not None

    # ── Score delta ───────────────────────────────────────────────────
    score_current = gs_current.score if gs_current else None
    score_previous = gs_previous.score if gs_previous else None
    score_delta = (score_current - score_previous) if (score_current is not None and score_previous is not None) else None
    score_tier = gs_current.tier if gs_current else None

    # ── Metric deltas ────────────────────────────────────────────────
    avg_views_current = snap_current.avg_views_per_video if snap_current else None
    avg_views_previous = snap_previous.avg_views_per_video if snap_previous else None
    _, avg_views_pct = _format_delta(avg_views_current, avg_views_previous)

    subs_current = snap_current.total_subscribers if snap_current else None
    subs_previous = snap_previous.total_subscribers if snap_previous else None
    subs_delta, subs_pct = _format_delta(subs_current, subs_previous)

    engagement_current = snap_current.engagement_rate if snap_current else None
    engagement_previous = snap_previous.engagement_rate if snap_previous else None
    _, engagement_pct = _format_delta(engagement_current, engagement_previous)

    # ── Evidence: strengths + concerns ────────────────────────────────
    strengths: list[EvidenceItem] = []
    concerns: list[EvidenceItem] = []

    if score_delta is not None and score_delta >= 3:
        direction = "increased" if score_delta > 0 else "improved"
        strengths.append(EvidenceItem(
            label=f"Growth Score {direction} from {score_previous} to {score_current}",
            detail=f"{abs(score_delta)}-point climb to the {score_tier} tier." if score_delta > 0 else "Growth Score changed.",
            pct_change=round((score_delta / score_previous) * 100, 1) if score_previous else None,
            category="score",
        ))

    if avg_views_pct is not None and avg_views_pct >= 5:
        strengths.append(EvidenceItem(
            label=f"Average views {_describe_pct(avg_views_pct)} {avg_views_pct:+.0f}%",
            detail=f"From {avg_views_previous:,.0f} to {avg_views_current:,.0f} per video" if avg_views_current and avg_views_previous else "",
            pct_change=round(avg_views_pct, 1),
            category="views",
        ))

    if subs_pct is not None and subs_pct >= 3:
        strengths.append(EvidenceItem(
            label=f"Subscribers {_describe_pct(subs_pct)} {subs_pct:+.0f}%",
            detail=f"Gained {abs(subs_delta):,.0f} subscribers" if subs_delta else "",
            pct_change=round(subs_pct, 1),
            category="subscribers",
        ))

    if engagement_pct is not None and engagement_pct >= 5:
        strengths.append(EvidenceItem(
            label=f"Engagement rate {_describe_pct(engagement_pct)} {engagement_pct:+.0f}%",
            detail=f"From {engagement_previous:.1%} to {engagement_current:.1%}" if engagement_current and engagement_previous else "",
            pct_change=round(engagement_pct, 1),
            category="engagement",
        ))

    if avg_views_pct is not None and avg_views_pct <= -5:
        concerns.append(EvidenceItem(
            label=f"Average views {_describe_pct(avg_views_pct)} {avg_views_pct:+.0f}%",
            detail=f"From {avg_views_previous:,.0f} to {avg_views_current:,.0f} per video" if avg_views_current and avg_views_previous else "",
            pct_change=round(avg_views_pct, 1),
            category="views",
            severity="high" if avg_views_pct <= -20 else "medium",
        ))

    if engagement_pct is not None and engagement_pct <= -5:
        concerns.append(EvidenceItem(
            label=f"Engagement rate {_describe_pct(engagement_pct)} {engagement_pct:+.0f}%",
            detail=f"From {engagement_previous:.1%} to {engagement_current:.1%}" if engagement_current and engagement_previous else "",
            pct_change=round(engagement_pct, 1),
            category="engagement",
            severity="high" if engagement_pct <= -15 else "medium",
        ))

    if subs_pct is not None and subs_pct <= -3:
        concerns.append(EvidenceItem(
            label=f"Subscribers {_describe_pct(subs_pct)} {subs_pct:+.0f}%",
            detail=f"Lost {abs(subs_delta):,.0f} subscribers" if subs_delta else "",
            pct_change=round(subs_pct, 1),
            category="subscribers",
            severity="high" if subs_pct <= -10 else "medium",
        ))

    # Add findings as concerns
    for f in findings:
        if f.severity in ("CRITICAL", "HIGH"):
            concerns.append(EvidenceItem(
                label=f.title,
                detail=f.description or "",
                category=f.category,
                severity=f.severity.lower(),
            ))
            if len(concerns) >= 6:
                break

    # ── Last week's mission ───────────────────────────────────────────
    completed_exps = [e for e in all_experiments if e.status == "completed"]
    running_exps = [e for e in all_experiments if e.status in ("running", "pending")]

    last_mission_obj: LastMission | None = None
    if report_previous and report_previous.next_30_day_goal:
        mission_status = "completed" if completed_exps else ("in_progress" if running_exps else "not_started")
        # Build outcome with the strongest available metric
        outcome_obj: MissionOutcome | None = None
        if avg_views_pct is not None and avg_views_previous is not None and avg_views_current is not None:
            outcome_obj = MissionOutcome(
                metric="Average views",
                before=round(avg_views_previous),
                after=round(avg_views_current),
                change_pct=round(avg_views_pct, 1),
            )
        elif subs_pct is not None and subs_previous is not None and subs_current is not None:
            outcome_obj = MissionOutcome(
                metric="Subscribers",
                before=subs_previous,
                after=subs_current,
                change_pct=round(subs_pct, 1),
            )
        elif engagement_pct is not None and engagement_previous is not None and engagement_current is not None:
            outcome_obj = MissionOutcome(
                metric="Engagement rate",
                before=round(engagement_previous * 100, 1),
                after=round(engagement_current * 100, 1),
                change_pct=round(engagement_pct, 1),
            )

        verdict_enum, verdict_label = _resolve_verdict(mission_status, avg_views_pct)

        last_mission_obj = LastMission(
            description=report_previous.next_30_day_goal,
            status=mission_status,
            outcome=outcome_obj,
            verdict=verdict_label,
            verdict_enum=verdict_enum.value,
        )
    elif report_latest and report_latest.next_30_day_goal:
        # First review — show the current mission as active
        last_mission_obj = LastMission(
            description=report_latest.next_30_day_goal,
            status="in_progress",
            outcome=None,
            verdict=VERDICT_LABELS[MissionVerdict.IN_PROGRESS],
            verdict_enum=MissionVerdict.IN_PROGRESS.value,
        )

    # ── New questions (Act 4) ─────────────────────────────────────────
    new_questions: list[str] = []

    for p in patterns:
        metrics = p.metrics or {}
        if p.pattern_type == "topic_cluster":
            best = metrics.get("best_cluster_name")
            worst = metrics.get("worst_cluster_name")
            if best and worst:
                new_questions.append(
                    f"We now know {best} content outperforms {worst} content. "
                    f"We still don't know whether shorter or longer versions of "
                    f"{best} content perform better for subscriber retention."
                )
                break
        elif p.pattern_type == "series_pattern":
            series = metrics.get("series_name", "your series content")
            new_questions.append(
                f"We now know {series} works well for your channel. "
                f"We still don't know the optimal publishing frequency for "
                f"this format to maximize growth without burnout."
            )
            break
        elif p.pattern_type == "title_pattern":
            best_range = metrics.get("best_range", "shorter")
            new_questions.append(
                f"We now know {best_range} titles perform better. "
                f"We still don't know which title keywords are most correlated "
                f"with high click-through rates for your audience."
            )
            break

    if len(new_questions) == 0 and has_history:
        new_questions.append(
            "Your data is still building. As we collect more analysis points, "
            "clearer questions about your content strategy will emerge."
        )
    elif len(new_questions) == 0:
        new_questions.append(
            "Once you have two or more analyses, we'll identify specific "
            "gaps in your strategy to explore."
        )

    # ── Next focus (Act 5) ────────────────────────────────────────────
    next_focus = report_latest.next_30_day_goal if report_latest else ""
    if not next_focus and patterns:
        top = patterns[0]
        actions = top.suggested_actions or []
        if actions:
            next_focus = actions[0]
    if not next_focus:
        next_focus = "Continue publishing consistently so we can gather enough data to identify your first growth opportunity."

    # ── Act 1: Executive review ───────────────────────────────────────
    review_text = _build_conclusion(
        has_history=has_history,
        score_current=score_current,
        score_delta=score_delta,
        score_tier=score_tier,
        strengths=[s.__dict__ for s in strengths],
        concerns=[c.__dict__ for c in concerns],
        last_mission=last_mission_obj,
        next_focus=next_focus,
        completed_exps=completed_exps,
    )

    review_obj = GrowthReview(
        has_review=True,
        has_history=has_history,
        review=review_text,
        evidence_strengths=strengths,
        evidence_concerns=concerns,
        last_mission=last_mission_obj,
        new_questions=new_questions,
        next_focus=next_focus,
    )

    return review_obj.to_dict()


def _resolve_verdict(
    status: str,
    avg_views_pct: float | None,
) -> tuple[MissionVerdict, str]:
    """Derive a verdict (enum + human-readable label) for the last mission."""
    if status == "completed":
        if avg_views_pct is not None and avg_views_pct >= 10:
            return MissionVerdict.SUCCESS, VERDICT_LABELS[MissionVerdict.SUCCESS]
        elif avg_views_pct is not None and avg_views_pct >= 3:
            return MissionVerdict.PARTIAL_SUCCESS, VERDICT_LABELS[MissionVerdict.PARTIAL_SUCCESS]
        elif avg_views_pct is not None and avg_views_pct <= -5:
            return MissionVerdict.UNSUCCESSFUL, VERDICT_LABELS[MissionVerdict.UNSUCCESSFUL]
        return MissionVerdict.INCONCLUSIVE, VERDICT_LABELS[MissionVerdict.INCONCLUSIVE]
    elif status == "in_progress":
        return MissionVerdict.IN_PROGRESS, VERDICT_LABELS[MissionVerdict.IN_PROGRESS]
    else:
        return MissionVerdict.NOT_STARTED, VERDICT_LABELS[MissionVerdict.NOT_STARTED]


def _build_conclusion(
    has_history: bool,
    score_current: int | None,
    score_delta: int | None,
    score_tier: str | None,
    strengths: list[dict],
    concerns: list[dict],
    last_mission: LastMission | None,
    next_focus: str,
    completed_exps: list,
) -> str:
    """Build a tight 2-3 sentence executive review.

    Answers: Did I improve? Why? What's next?
    Avoids repeating the score signal when it's already in strengths.
    """
    parts: list[str] = []

    score_already_covered = any(
        s.get("category") == "score" and s.get("pct_change") is not None
        for s in strengths
    )

    # ── Opening: overall direction ────────────────────────────────────
    if not has_history:
        if score_current is not None:
            parts.append(
                f"This is your first Growth Review. Your channel has a Growth Score "
                f"of {score_current} ({score_tier}). This establishes your baseline — "
                f"future reviews will track your progress."
            )
        else:
            parts.append(
                "This is your first Growth Review. We've analyzed your channel "
                "and established a baseline for future tracking."
            )
    elif score_delta is not None and not score_already_covered:
        if score_delta >= 5:
            parts.append(
                f"Your strategy is delivering. The Growth Score rose "
                f"{score_delta} points to {score_current} ({score_tier})."
            )
        elif score_delta >= 1:
            parts.append(
                f"Your channel is moving in the right direction. The Growth Score "
                f"edged up {score_delta} points to {score_current} ({score_tier})."
            )
        elif score_delta <= -5:
            parts.append(
                f"Your Growth Score dropped {abs(score_delta)} points to {score_current} "
                f"({score_tier}). Let's examine what changed."
            )
        else:
            parts.append(
                f"Your Growth Score held steady at {score_current} ({score_tier}), "
                f"consistent with incremental progress."
            )

    # ── Middle: strongest signal (skip if it's score and already covered) ─
    if strengths:
        top = strengths[0]
        # If the top strength is the score and we already wrote about score, skip it
        if not (top.get("category") == "score" and score_already_covered):
            pct_text = f" ({top['pct_change']:+.0f}%)" if top.get("pct_change") is not None else ""
            parts.append(f"{top['label']}{pct_text}.")

    if completed_exps:
        parts.append(
            f"You have {len(completed_exps)} completed experiment{'s' if len(completed_exps) > 1 else ''} "
            f"since the last review."
        )

    # ── If concerns outweigh strengths, acknowledge them ─────────────
    if concerns and not strengths:
        top_concern = concerns[0]
        parts.append(
            f"The largest signal is a decline in {top_concern['label'].lower()}."
        )

    # ── Closing: what's next ─────────────────────────────────────────
    if last_mission and last_mission.status == "completed":
        parts.append(f"Your last mission appears complete — {next_focus}.")
    elif next_focus:
        parts.append(f"The next focus: {next_focus}")

    review_text = " ".join(parts)
    if not review_text:
        review_text = (
            "Your analysis is complete. As you continue running analyses, "
            "your Growth Review will track what's working and what needs attention."
        )
    return review_text


@router.get("/growth")
async def growth_score(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the latest GrowthScore summary with history delta."""
    profile, _ = await _resolve_creator(request, db)

    result = await db.execute(
        select(GrowthScore)
        .where(GrowthScore.creator_profile_id == profile.id)
        .order_by(desc(GrowthScore.recorded_at))
        .limit(2)
    )
    scores = result.scalars().all()

    if not scores:
        return {
            "score": None,
            "tier": None,
            "summary": None,
            "potential_low": None,
            "potential_high": None,
            "previous_score": None,
            "delta": None,
            "recorded_at": None,
        }

    latest = scores[0]
    previous = scores[1] if len(scores) > 1 else None

    return {
        "score": latest.score,
        "tier": latest.tier,
        "summary": latest.summary,
        "potential_low": latest.potential_low,
        "potential_high": latest.potential_high,
        "previous_score": previous.score if previous else None,
        "delta": latest.score - previous.score if previous else None,
        "recorded_at": latest.recorded_at.isoformat() if latest.recorded_at else None,
    }


@router.get("/patterns")
async def pattern_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return intelligence patterns for the authenticated user."""
    profile, _ = await _resolve_creator(request, db)

    result = await db.execute(
        select(PipelinePattern)
        .where(PipelinePattern.creator_profile_id == profile.id)
        .order_by(PipelinePattern.impact_score.desc())
        .limit(20)
    )
    patterns = result.scalars().all()

    return {
        "patterns": [
            {
                "id": str(p.id),
                "type": p.pattern_type,
                "summary": p.summary,
                "explanation": p.explanation,
                "confidence": p.confidence,
                "impact": p.impact,
                "impact_score": p.impact_score,
                "metrics": p.metrics,
                "evidence": p.evidence,
                "suggested_actions": p.suggested_actions,
            }
            for p in patterns
        ],
        "total": len(patterns),
    }


@router.get("/pipeline")
async def pipeline_artifacts(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return all pipeline artifacts (Evidence, Claims, Recommendations, Experiments)."""
    profile, _ = await _resolve_creator(request, db)

    # Evidence (join through Finding.creator_profile_id)
    ev_result = await db.execute(
        select(PipelineEvidence)
        .join(Finding, Finding.id == PipelineEvidence.source_finding_id)
        .where(Finding.creator_profile_id == profile.id)
        .order_by(desc(PipelineEvidence.id))
        .limit(20)
    )
    evidence_list = ev_result.scalars().all()

    # Claims
    cl_result = await db.execute(
        select(PipelineClaim)
        .where(PipelineClaim.creator_profile_id == profile.id)
        .order_by(desc(PipelineClaim.id))
        .limit(20)
    )
    claim_list = cl_result.scalars().all()

    # Recommendations
    rec_result = await db.execute(
        select(PipelineRecommendation)
        .where(PipelineRecommendation.creator_profile_id == profile.id)
        .order_by(desc(PipelineRecommendation.id))
        .limit(20)
    )
    rec_list = rec_result.scalars().all()

    # Experiments
    exp_result = await db.execute(
        select(PipelineExperiment)
        .where(PipelineExperiment.creator_profile_id == profile.id)
        .order_by(desc(PipelineExperiment.created_at))
        .limit(20)
    )
    exp_list = exp_result.scalars().all()

    # Executive summary (latest report)
    report = None
    rpt_result = await db.execute(
        select(ChannelReport)
        .where(ChannelReport.creator_profile_id == profile.id)
        .order_by(desc(ChannelReport.created_at))
        .limit(1)
    )
    report_row = rpt_result.scalar_one_or_none()
    if report_row:
        report = {
            "version": report_row.version,
            "thesis": report_row.thesis,
            "biggest_opportunity": report_row.biggest_opportunity,
            "biggest_risk": report_row.biggest_risk,
            "what_surprised_us": report_row.what_surprised_us,
            "next_30_day_goal": report_row.next_30_day_goal,
            "channel_story": report_row.channel_story,
            "recommendation_ids": report_row.recommendation_ids,
        }

    return {
        "evidence": [
            {
                "id": str(e.id),
                "source_rule_id": e.source_rule_id,
                "confidence": e.confidence,
                "explanation": e.explanation,
            }
            for e in evidence_list
        ],
        "claims": [
            {
                "id": str(c.id),
                "category": c.category,
                "severity": c.severity,
                "summary": c.summary,
                "rationale": c.rationale,
            }
            for c in claim_list
        ],
        "recommendations": [
            {
                "id": str(r.id),
                "priority": r.priority.value
                if hasattr(r.priority, "value")
                else r.priority,
                "category": r.category,
                "title": r.title,
                "description": r.description,
                "expected_outcome": r.expected_outcome,
                "details": r.details,
            }
            for r in rec_list
        ],
        "experiments": [
            {
                "id": str(e.id),
                "hypothesis": e.hypothesis,
                "status": e.status.value
                if hasattr(e.status, "value")
                else e.status,
                "success_metric": e.success_metric,
            }
            for e in exp_list
        ],
        "executive_summary": report,
    }


@router.get("/videos")
async def video_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return imported videos for the authenticated user."""
    profile, _ = await _resolve_creator(request, db)

    result = await db.execute(
        select(Video)
        .options(joinedload(Video.metrics))
        .where(
            Video.creator_profile_id == profile.id,
            Video.is_deleted.is_(False),
        )
        .order_by(desc(Video.published_at))
        .limit(50)
    )
    videos = result.unique().scalars().all()

    def latest_metrics(v: Video) -> dict:
        if not v.metrics:
            return {}
        m = max(v.metrics, key=lambda x: x.recorded_at)
        return {
            "view_count": m.view_count,
            "like_count": m.like_count,
            "comment_count": m.comment_count,
        }

    return {
        "videos": [
            {
                "id": str(v.id),
                "title": v.title,
                "thumbnail_url": v.thumbnail_url,
                "published_at": v.published_at.isoformat() if v.published_at else None,
                "duration_seconds": v.duration_seconds,
                "url": v.url,
                "platform_video_id": v.platform_video_id,
                **latest_metrics(v),
            }
            for v in videos
        ],
        "total": len(videos),
    }
