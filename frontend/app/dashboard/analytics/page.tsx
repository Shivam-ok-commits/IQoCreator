"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { CreatorThemeProvider } from "@/components/theme/CreatorThemeProvider";
import { useCreatorTheme } from "@/hooks/useCreatorTheme";
import { CreatorHero } from "@/components/creator/CreatorHero";
import { api, type AnalyticsSummary, type GrowthScoreData, type GrowthReviewData, type VideoItem } from "@/services/api";
import type { ThemeTokens } from "@/components/theme/ThemeTokens";
import Link from "next/link";

interface PipelineData {
  evidence: Array<{ id: string; source_rule_id: string; confidence: number; explanation: string }>;
  claims: Array<{ id: string; category: string; severity: string; summary: string; rationale: string }>;
  recommendations: Array<{
    id: string;
    priority: string;
    category: string;
    title: string;
    description: string;
    expected_outcome: string;
    details: {
      version: number;
      type: string;
      headline: string;
      observation: string;
      evidence: string[];
      why_it_matters: string;
      action_plan: string[];
      expected_outcome: string;
      risk_of_doing_nothing: string;
      strength: {
        level: string;
        rating: number;
        because: string[];
      };
      impact: number;
      supporting_video_ids: string[];
      supporting_videos: Array<{ title: string; views: number; type: string }>;
      why_now: string;
    } | null;
  }>;
  experiments: Array<{ id: string; hypothesis: string; status: string; success_metric: string }>;
  executive_summary: {
    version: number;
    thesis: string;
    biggest_opportunity: string;
    biggest_risk: string;
    what_surprised_us: string | null;
    next_30_day_goal: string;
    channel_story: string | null;
    recommendation_ids: string[];
  } | null;
}

function consultantTitle(original: string): string {
  const map: Record<string, string> = {
    "Increase upload cadence": "Publish on a consistent weekly schedule",
    "Improve audience retention and engagement": "Make every second count in your first 30 seconds",
    "Increase long-form content balance": "Balance shorts with long-form content",
    "Improve topic and title selection": "Your next upload should target searchable topics",
    "Continue publishing — collect data for optimization": "Keep publishing — your data will reveal the path",
    "Low upload frequency": "You're not uploading enough to grow",
    "Low engagement rate": "Your audience isn't engaging enough",
    "High shorts ratio": "Too many shorts — add long-form content",
    "Low average views": "Your videos aren't reaching enough viewers",
    "Inconsistent publishing schedule": "Your upload schedule is too unpredictable",
    "New channel — focus on discovery": "Focus on being found",
  };
  return map[original] || original;
}

function findTopBottleneck(findings: AnalyticsSummary["findings"]) {
  const order = ["CRITICAL", "HIGH", "MEDIUM", "INFO"];
  for (const sev of order) {
    const match = findings.items.find((f) => f.severity === sev);
    if (match) return match;
  }
  return null;
}

function formatCount(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function AnalyticsContent() {
  const { user } = useAuth();
  const { theme } = useCreatorTheme();
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [pipeline, setPipeline] = useState<PipelineData | null>(null);
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [growthData, setGrowthData] = useState<GrowthScoreData | null>(null);
  const [review, setReview] = useState<GrowthReviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});
  const [showTechDetails, setShowTechDetails] = useState(false);
  const [showInsights, setShowInsights] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [summary, pipelineData, videosRes, growth, reviewData] = await Promise.all([
          api.getAnalyticsSummary(),
          api.getPipeline(),
          api.getVideos(),
          api.getGrowth(),
          api.getGrowthReview(),
        ]);
        setData(summary);
        setPipeline(pipelineData);
        setVideos(videosRes.videos ?? []);
        setGrowthData(growth);
        setReview(reviewData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load analytics");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const bottleneck = useMemo(() => data ? findTopBottleneck(data.findings) : null, [data]);
  const hasAnalysis = data && data.findings.total > 0;

  const toggleSection = useCallback((id: string) => {
    setExpandedSections((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  if (!user) return null;

  const fontSize = (px: number) => ({ fontSize: px, lineHeight: 1.3 });

  return (
    <main className="min-h-screen" style={{ background: theme.background }}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        <div className="mb-6">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 transition-colors"
            style={{ color: theme.textSecondary, fontSize: 14 }}
            onMouseEnter={(e) => (e.currentTarget.style.color = theme.primary)}
            onMouseLeave={(e) => (e.currentTarget.style.color = theme.textSecondary)}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5" />
              <path d="m12 19-7-7 7-7" />
            </svg>
            Back to Dashboard
          </Link>
        </div>

        <CreatorHero data={user} />

        <div className="mt-8">
          <h1 className="font-display mb-8" style={{ ...fontSize(32), color: theme.textPrimary }}>
            Channel Growth Score
          </h1>

          {loading && (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin w-8 h-8 rounded-full border-2" style={{ borderColor: `${theme.primary}30`, borderTopColor: theme.primary }} />
            </div>
          )}

          {error && (
            <div className="rounded-2xl p-8 text-center" style={{ background: theme.surface, border: `1px solid ${theme.border}` }}>
              <p style={{ color: theme.danger, fontSize: 16 }}>{error}</p>
            </div>
          )}

          {data && !hasAnalysis && (
            <div className="rounded-2xl p-8 text-center" style={{ background: theme.surface, border: `1px solid ${theme.border}` }}>
              <p style={{ color: theme.textSecondary, fontSize: 20 }}>
                Analysis has not been run yet. Click "Run Analysis" to generate insights.
              </p>
            </div>
          )}

          {data && hasAnalysis && (
            <div className="space-y-8">
              {/* ════ 1. Channel Growth Score ════ */}
              <Card theme={theme}>
                <div className="flex items-start justify-between flex-wrap gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div style={{ fontSize: 36, fontWeight: 700, color: theme.textPrimary, lineHeight: 1 }}>
                        {growthData?.score ?? "—"}
                        <span style={{ fontSize: 16, fontWeight: 400, color: theme.textSecondary }}>/100</span>
                      </div>
                      {growthData?.previous_score != null && growthData.delta != null && (
                        <div style={{
                          fontSize: 14, fontWeight: 600, padding: "2px 8px", borderRadius: 6,
                          color: growthData.delta >= 0 ? theme.success : theme.danger,
                          background: growthData.delta >= 0 ? `${theme.success}15` : `${theme.danger}15`,
                        }}>
                          {growthData.delta >= 0 ? "+" : ""}{growthData.delta}
                          <span style={{ fontSize: 11, fontWeight: 400, marginLeft: 2 }}>from {growthData.previous_score}</span>
                        </div>
                      )}
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 600, color: theme.textPrimary, marginBottom: 2 }}>
                      {growthData?.tier ?? "—"}
                    </div>
                    {growthData?.summary && (
                      <p style={{ fontSize: 15, color: theme.textSecondary, lineHeight: 1.5, marginBottom: 4 }}>
                        {growthData.summary}
                      </p>
                    )}
                    {growthData?.potential_low != null && growthData?.potential_high != null && (
                      <div style={{ fontSize: 14, color: theme.primary, fontWeight: 500 }}>
                        Growth potential: +{growthData.potential_low}–{growthData.potential_high}% average views
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {growthData?.score != null && (
                      <div className="flex gap-0.5">
                        {[1, 2, 3, 4, 5].map((s) => (
                          <svg key={s} width="20" height="20" viewBox="0 0 24 24" fill={s <= Math.round(growthData.score! / 20) ? "#f59e0b" : `${theme.border}`}>
                            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                          </svg>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Channel metrics row */}
                <div className="grid grid-cols-3 gap-4 mt-5 pt-5" style={{ borderTop: `1px solid ${theme.border}` }}>
                  <MetricBox theme={theme} label="Subscribers" value={data.channel_metrics.subscriber_count} />
                  <MetricBox theme={theme} label="Total Views" value={data.channel_metrics.total_views} />
                  <MetricBox theme={theme} label="Videos" value={data.channel_metrics.total_videos} />
                </div>
              </Card>

              {/* ════ 2. Growth Review — consulting-style review ════ */}
              <GrowthReviewCard theme={theme} review={review} />

              {/* ════ 3. Biggest Bottleneck (detailed) ════ */}
              {bottleneck && (
                <Card theme={theme}>
                  <div style={{ fontSize: 14, color: theme.textSecondary, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    What to fix this week
                  </div>
                  <div className="flex items-start gap-3 mb-3">
                    <div style={{
                      width: 10, height: 10, borderRadius: "50%", marginTop: 12,
                      background: bottleneck.severity === "CRITICAL" || bottleneck.severity === "HIGH" ? theme.danger : "#f59e0b",
                      flexShrink: 0,
                    }} />
                    <div>
                      <h2 style={{ ...fontSize(28), fontWeight: 600, color: theme.textPrimary, marginBottom: 6 }}>
                        {consultantTitle(bottleneck.title)}
                      </h2>
                      <p style={{ ...fontSize(20), color: theme.textSecondary, lineHeight: 1.5 }}>
                        {bottleneck.description}
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={() => toggleSection("bottleneck")}
                    className="flex items-center gap-1.5 mt-3 transition-opacity hover:opacity-80"
                    style={{ fontSize: 16, color: theme.primary, background: "none", border: "none", cursor: "pointer", padding: 0 }}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                      style={{ transform: expandedSections["bottleneck"] ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
                      <path d="m9 18 6-6-6-6" />
                    </svg>
                    {expandedSections["bottleneck"] ? "Hide evidence" : "Why?"}
                  </button>
                  {expandedSections["bottleneck"] && pipeline && (
                    <div className="mt-3 space-y-2 pl-5 border-l-2" style={{ borderColor: `${theme.primary}20` }}>
                      {pipeline.evidence
                        .filter((e) => e.source_rule_id === bottleneck.rule_id)
                        .map((e) => (
                          <div key={e.id}>
                            <div style={{ fontSize: 16, color: theme.textPrimary, marginBottom: 2 }}>
                              {e.explanation}
                            </div>
                            <div style={{ fontSize: 14, color: theme.textSecondary }}>
                              Confidence: {(e.confidence * 100).toFixed(0)}%
                            </div>
                          </div>
                        ))}
                      {pipeline.evidence.filter((e) => e.source_rule_id === bottleneck.rule_id).length === 0 && (
                        <div style={{ fontSize: 14, color: theme.textSecondary }}>No detailed evidence available.</div>
                      )}
                    </div>
                  )}
                </Card>
              )}

              {/* ════ 4. Executive Summary ════ */}
              {pipeline?.executive_summary && (
                <Card theme={theme}>
                  <div style={{ fontSize: 14, color: theme.textSecondary, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Channel analysis
                  </div>
                  <p style={{ ...fontSize(18), color: theme.textPrimary, lineHeight: 1.7, marginBottom: 20 }}>
                    {pipeline.executive_summary.thesis}
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div className="rounded-xl p-4" style={{ background: `${theme.success}08`, border: `1px solid ${theme.success}20` }}>
                      <div style={{ fontSize: 13, color: theme.textSecondary, marginBottom: 2 }}>Your fastest path to growth</div>
                      <div style={{ fontSize: 17, fontWeight: 600, color: theme.success }}>
                        {pipeline.executive_summary.biggest_opportunity}
                      </div>
                    </div>
                    <div className="rounded-xl p-4" style={{ background: `${theme.danger}08`, border: `1px solid ${theme.danger}20` }}>
                      <div style={{ fontSize: 13, color: theme.textSecondary, marginBottom: 2 }}>What's holding this channel back</div>
                      <div style={{ fontSize: 17, fontWeight: 600, color: theme.danger }}>
                        {pipeline.executive_summary.biggest_risk}
                      </div>
                    </div>
                    <div className="rounded-xl p-4" style={{ background: `${theme.primary}08`, border: `1px solid ${theme.primary}20` }}>
                      <div style={{ fontSize: 13, color: theme.textSecondary, marginBottom: 2 }}>Your focus for the next 30 days</div>
                      <div style={{ fontSize: 17, fontWeight: 600, color: theme.primary }}>
                        {pipeline.executive_summary.next_30_day_goal}
                      </div>
                    </div>
                  </div>

                  {pipeline.executive_summary.what_surprised_us && (
                    <div className="rounded-xl p-4 mb-4" style={{ background: `${theme.textPrimary}05`, border: `1px solid ${theme.border}` }}>
                      <div style={{ fontSize: 13, color: theme.textSecondary, marginBottom: 2 }}>What surprised us</div>
                      <div style={{ fontSize: 16, color: theme.textPrimary, lineHeight: 1.5 }}>
                        {pipeline.executive_summary.what_surprised_us}
                      </div>
                    </div>
                  )}

                  {pipeline.executive_summary.channel_story && (
                    <button
                      onClick={() => toggleSection("channel_story")}
                      className="flex items-center gap-1.5 transition-opacity hover:opacity-80"
                      style={{ fontSize: 16, color: theme.primary, background: "none", border: "none", cursor: "pointer", padding: 0 }}
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                        style={{ transform: expandedSections["channel_story"] ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
                        <path d="m9 18 6-6-6-6" />
                      </svg>
                      {expandedSections["channel_story"] ? "Hide channel story" : "Channel story"}
                    </button>
                  )}
                  {expandedSections["channel_story"] && pipeline.executive_summary.channel_story && (
                    <div className="mt-3 rounded-xl p-4" style={{ background: `${theme.textPrimary}05`, border: `1px solid ${theme.border}` }}>
                      <div style={{ fontSize: 16, color: theme.textPrimary, lineHeight: 1.7, fontStyle: "italic" }}>
                        {pipeline.executive_summary.channel_story}
                      </div>
                    </div>
                  )}
                </Card>
              )}

              {/* ════ 5. This week's experiments ════ */}
              {pipeline && pipeline.recommendations.length > 0 && (
                <Card theme={theme}>
                  <div style={{ fontSize: 14, color: theme.textSecondary, marginBottom: 16, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    This week's experiments
                  </div>
                  <div className="space-y-8">
                    {pipeline.recommendations.slice(0, 3).map((r, i) => {
                      const d = r.details;
                      const cardKey = `rec_reasoning_${r.id}`;
                      const showReasoning = expandedSections[cardKey] ?? false;
                      const priorityColor = r.priority === "CRITICAL" ? theme.danger
                        : r.priority === "HIGH" ? "#f59e0b"
                        : theme.textSecondary;
                      return (
                        <div key={r.id}>
                          <div className="flex items-start gap-3">
                            <div style={{
                              width: 28, height: 28, borderRadius: "50%",
                              background: `${priorityColor}15`, color: priorityColor,
                              display: "flex", alignItems: "center", justifyContent: "center",
                              fontSize: 14, fontWeight: 600, flexShrink: 0, marginTop: 2,
                            }}>
                              {i + 1}
                            </div>
                            <div className="flex-1 min-w-0">
                              {/* What did we discover? (Headline) */}
                              <h3 style={{ ...fontSize(22), fontWeight: 600, color: theme.textPrimary, marginBottom: 8 }}>
                                {d?.headline ?? r.title}
                              </h3>

                              {d ? (
                                <>
                                  {/* Why do we believe it? */}
                                  <p className="mb-3" style={{ fontSize: 16, color: theme.textSecondary, lineHeight: 1.6 }}>
                                    {d.evidence.slice(0, 2).join(". ")}
                                    {d.evidence.length > 2 && ` (and ${d.evidence.length - 2} more indicators)`}
                                  </p>

                                  {/* Visual proof: supporting videos with bars */}
                                  {d.supporting_videos.length > 0 && (
                                    <div className="mb-4 space-y-2">
                                      {d.supporting_videos.slice(0, 4).map((v: { title: string; views: number; type: string }, vi: number) => {
                                        const maxViews = Math.max(...d.supporting_videos.map((sv: { views: number }) => sv.views), 1);
                                        const barWidth = Math.max(4, (v.views / maxViews) * 100);
                                        const barColor = v.type === "worst" ? theme.danger : theme.primary;
                                        return (
                                          <div key={vi} className="flex items-center gap-3">
                                            <div className="flex-1 min-w-0" style={{ textAlign: "right" }}>
                                              <span style={{ fontSize: 14, color: theme.textSecondary }}>{v.title}</span>
                                            </div>
                                            <div className="flex-shrink-0" style={{ width: 120, height: 16, background: `${theme.border}40`, borderRadius: 4, overflow: "hidden" }}>
                                              <div style={{ width: `${barWidth}%`, height: "100%", background: barColor, borderRadius: 4, opacity: 0.7 }} />
                                            </div>
                                            <div className="flex-shrink-0" style={{ width: 60, textAlign: "right" }}>
                                              <span style={{ fontSize: 14, fontWeight: 600, color: theme.textPrimary }}>{v.views.toLocaleString()}</span>
                                            </div>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  )}

                                  {/* What should you do this week? (Mission) */}
                                  {d.action_plan.length > 0 && (
                                    <div className="mb-3 rounded-xl p-4" style={{ background: `${theme.primary}08`, border: `1px solid ${theme.border}` }}>
                                      <div style={{ fontSize: 13, color: theme.textSecondary, marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                                        This week's mission
                                      </div>
                                      <div style={{ fontSize: 16, fontWeight: 600, color: theme.textPrimary, lineHeight: 1.5 }}>
                                        {d.action_plan[0]}
                                      </div>
                                      {d.action_plan.length > 1 && (
                                        <div className="mt-2 space-y-1">
                                          {d.action_plan.slice(1).map((step: string, ai: number) => (
                                            <div key={ai} className="flex items-start gap-2" style={{ fontSize: 14, color: theme.textSecondary }}>
                                              <span style={{ color: theme.primary, fontSize: 12 }}>•</span>
                                              <span>{step}</span>
                                            </div>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  )}

                                  {/* What result? + Why this comes first */}
                                  <div className="flex flex-wrap items-center gap-4 mb-2">
                                    <div>
                                      <span style={{ fontSize: 13, color: theme.textSecondary }}>Expected result</span>
                                      <div style={{ fontSize: 18, fontWeight: 700, color: theme.primary }}>
                                        {d.expected_outcome}
                                      </div>
                                    </div>
                                    <div>
                                      <span style={{ fontSize: 13, color: theme.textSecondary }}>Strength</span>
                                      <div style={{ fontSize: 15, fontWeight: 600, color: theme.textPrimary }}>
                                        {d.strength.level} {"★".repeat(d.strength.rating)}{"☆".repeat(Math.max(0, 5 - d.strength.rating))}
                                      </div>
                                    </div>
                                  </div>

                                  {/* Why this comes first (replaces priority badge) */}
                                  {d.why_now && (
                                    <div className="flex items-start gap-2 mt-2 p-3 rounded-lg" style={{ background: `${theme.textPrimary}05`, border: `1px solid ${theme.border}` }}>
                                      <span style={{ fontSize: 13, color: theme.primary, fontWeight: 600, whiteSpace: "nowrap" }}>
                                        Why this comes first
                                      </span>
                                      <span style={{ fontSize: 14, color: theme.textSecondary, lineHeight: 1.5 }}>
                                        {d.why_now}
                                      </span>
                                    </div>
                                  )}

                                  {/* Show reasoning toggle */}
                                  <button
                                    onClick={() => toggleSection(cardKey)}
                                    className="flex items-center gap-1.5 transition-opacity hover:opacity-80"
                                    style={{ fontSize: 15, color: theme.primary, background: "none", border: "none", cursor: "pointer", padding: 0, marginTop: 8 }}
                                  >
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                                      style={{ transform: showReasoning ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
                                      <path d="m9 18 6-6-6-6" />
                                    </svg>
                                    {showReasoning ? "Hide reasoning" : "Show reasoning"}
                                  </button>

                                  {showReasoning && (
                                    <div className="mt-3 space-y-4 pl-4" style={{ borderLeft: `2px solid ${theme.border}` }}>
                                      {/* Evidence */}
                                      {d.evidence.length > 0 && (
                                        <div>
                                          <div style={{ fontWeight: 600, color: theme.textPrimary, marginBottom: 4, fontSize: 15 }}>Evidence</div>
                                          <div className="space-y-1">
                                            {d.evidence.map((line: string, ei: number) => (
                                              <div key={ei} className="flex items-start gap-2" style={{ fontSize: 14, color: theme.textSecondary }}>
                                                <span style={{ color: theme.primary, fontSize: 12 }}>•</span>
                                                <span>{line}</span>
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}

                                      {/* Why it matters */}
                                      <div style={{ fontSize: 14, color: theme.textSecondary, lineHeight: 1.6 }}>
                                        <span style={{ fontWeight: 600, color: theme.textPrimary }}>Why it matters. </span>
                                        {d.why_it_matters}
                                      </div>

                                      {/* Risk of doing nothing */}
                                      <div className="p-3 rounded-lg" style={{ background: `${theme.danger}10`, border: `1px solid ${theme.danger}20`, fontSize: 14, color: theme.textSecondary, lineHeight: 1.5 }}>
                                        <span style={{ fontWeight: 600, color: theme.danger }}>Risk of doing nothing. </span>
                                        {d.risk_of_doing_nothing}
                                      </div>

                                      {/* Full strength breakdown */}
                                      <div>
                                        <div style={{ fontWeight: 600, color: theme.textPrimary, marginBottom: 4, fontSize: 15 }}>Recommendation strength</div>
                                        <div className="flex items-center gap-2" style={{ fontSize: 15, color: theme.textPrimary }}>
                                          {d.strength.level}
                                          <span style={{ color: theme.textSecondary, fontWeight: 400 }}>
                                            {"★".repeat(d.strength.rating)}{"☆".repeat(Math.max(0, 5 - d.strength.rating))}
                                          </span>
                                        </div>
                                        {d.strength.because.length > 0 && (
                                          <div className="mt-1 space-y-0.5">
                                            {d.strength.because.map((reason: string, bi: number) => (
                                              <div key={bi} style={{ fontSize: 13, color: theme.textSecondary }}>
                                                • {reason}
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  )}
                                </>
                              ) : (
                                /* Fallback for recommendations without details */
                                <>
                                  <p style={{ fontSize: 16, color: theme.textSecondary, marginBottom: 8, lineHeight: 1.5 }}>
                                    {r.description}
                                  </p>
                                  <div className="flex flex-wrap gap-3 mt-2">
                                    <span style={{
                                      fontSize: 13, padding: "3px 10px", borderRadius: 999,
                                      background: `${priorityColor}15`, color: priorityColor,
                                      fontWeight: 500,
                                    }}>
                                      {r.priority} priority
                                    </span>
                                    <span style={{ fontSize: 13, color: theme.primary }}>
                                      Expected: {r.expected_outcome}
                                    </span>
                                  </div>
                                </>
                              )}
                            </div>
                          </div>
                          {i < 2 && pipeline.recommendations.length > 1 && (
                            <div style={{ height: 1, background: theme.border, marginTop: 24 }} />
                          )}
                        </div>
                      );
                    })}
                  </div>
                </Card>
              )}

              {/* ════ 6. Expected Results ════ */}
              {pipeline && pipeline.recommendations.length > 0 && (
                <Card theme={theme}>
                  <div style={{ fontSize: 14, color: theme.textSecondary, marginBottom: 16, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Expected impact
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {pipeline.recommendations.slice(0, 3).map((r, i) => {
                      const d = r.details;
                      const outcome = d?.expected_outcome ?? r.expected_outcome;
                      const label = d?.headline ?? r.title;
                      const strengthLabel = d ? `${d.strength.level} (${"★".repeat(d.strength.rating)}${"☆".repeat(Math.max(0, 5 - d.strength.rating))})` : "";
                      return (
                        <div key={r.id} className="rounded-xl p-4" style={{ background: `${theme.primary}08`, border: `1px solid ${theme.border}` }}>
                          <div style={{ fontSize: 13, color: theme.textSecondary, marginBottom: 4 }}>
                            Action {i + 1}
                          </div>
                          <div style={{ fontSize: 16, fontWeight: 600, color: theme.primary, marginBottom: 2, lineHeight: 1.3 }}>
                            {outcome}
                          </div>
                          <div style={{ fontSize: 13, color: theme.textSecondary }}>
                            {label}
                          </div>
                          {strengthLabel && <div style={{ fontSize: 12, color: theme.textSecondary, marginTop: 4, opacity: 0.7 }}>{strengthLabel}</div>}
                        </div>
                      );
                    })}
                  </div>
                  {/* 30-Day Action Plan as timeline */}
                  {pipeline.experiments.length > 0 && (
                    <div className="mt-6 pt-5" style={{ borderTop: `1px solid ${theme.border}` }}>
                      <div style={{ fontSize: 13, color: theme.textSecondary, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                        30-day action plan
                      </div>
                      <div className="space-y-3">
                        {pipeline.experiments.slice(0, 4).map((exp, i) => {
                          const weekColors = [theme.primary, "#f59e0b", theme.success, "#8b5cf6"];
                          const weekLabels = ["Week 1", "Week 2", "Week 3", "Week 4"];
                          const color = weekColors[i] || theme.textSecondary;
                          const task = exp.hypothesis.replace(/^Implementing "|" will lead to.*$/g, "").trim();
                          return (
                            <div key={exp.id} className="flex gap-3">
                              <div className="flex flex-col items-center" style={{ width: 20 }}>
                                <div style={{ width: 10, height: 10, borderRadius: "50%", background: color, flexShrink: 0 }} />
                                {i < 3 && <div style={{ width: 1.5, flex: 1, background: `${color}25` }} />}
                              </div>
                              <div className="flex-1 pb-1">
                                <div style={{ fontSize: 13, color, fontWeight: 600 }}>{weekLabels[i]}</div>
                                <div style={{ fontSize: 15, color: theme.textPrimary }}>{task}</div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </Card>
              )}

              {/* ════ 7. Recent Video Performance ════ */}
              {videos.length > 0 && (
                <Card theme={theme}>
                  <div style={{ fontSize: 14, color: theme.textSecondary, marginBottom: 16, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Recent video performance
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {videos.slice(0, 6).map((v) => (
                      <a
                        key={v.id}
                        href={v.url || "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="rounded-xl overflow-hidden transition-all duration-200 block"
                        style={{ background: `${theme.background}`, border: `1px solid ${theme.border}` }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = `${theme.primary}30`;
                          e.currentTarget.style.boxShadow = `0 0 20px -8px ${theme.glow}`;
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = theme.border;
                          e.currentTarget.style.boxShadow = "none";
                        }}
                      >
                        {v.thumbnail_url && (
                          <div className="aspect-video bg-black/40 overflow-hidden">
                            <img src={v.thumbnail_url} alt={v.title} className="w-full h-full object-cover" loading="lazy" />
                          </div>
                        )}
                        <div className="p-3">
                          <div className="text-xs line-clamp-2 mb-2" style={{ color: theme.textPrimary, fontWeight: 500, lineHeight: 1.3 }}>
                            {v.title}
                          </div>
                          <div className="flex items-center gap-3 text-xs" style={{ color: theme.textSecondary }}>
                            {v.view_count != null && <span>{formatCount(v.view_count)} views</span>}
                            {v.like_count != null && <span>{formatCount(v.like_count)} likes</span>}
                            {v.published_at && (
                              <span className="ml-auto">{new Date(v.published_at).toLocaleDateString()}</span>
                            )}
                          </div>
                        </div>
                      </a>
                    ))}
                  </div>
                  {videos.length > 6 && (
                    <Link
                      href="/dashboard/content"
                      className="inline-block mt-4 text-sm transition-colors"
                      style={{ color: theme.primary }}
                    >
                      View all {videos.length} videos →
                    </Link>
                  )}
                </Card>
              )}

              {/* ════ 8. Insights (expandable) ════ */}
              {pipeline && pipeline.claims.length > 0 && (
                <div>
                  <button
                    onClick={() => setShowInsights(!showInsights)}
                    className="flex items-center gap-2 w-full py-3 px-4 rounded-2xl transition-colors"
                    style={{ background: theme.surface, border: `1px solid ${theme.border}`, color: theme.textSecondary, cursor: "pointer", fontSize: 14 }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                      style={{ transform: showInsights ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
                      <path d="m9 18 6-6-6-6" />
                    </svg>
                    Insights
                    <span style={{ marginLeft: "auto", color: theme.textSecondary, opacity: 0.6 }}>
                      {pipeline.claims.length} items
                    </span>
                  </button>
                  {showInsights && (
                    <div className="mt-4 space-y-3">
                      {pipeline.claims.map((c) => (
                        <div key={c.id} className="rounded-xl p-4" style={{ background: theme.surface, border: `1px solid ${theme.border}` }}>
                          <div className="flex items-center gap-2 mb-1">
                            <span style={{
                              fontSize: 11, padding: "1px 6px", borderRadius: 4, textTransform: "uppercase",
                              background: c.severity === "CRITICAL" || c.severity === "HIGH" ? `${theme.danger}15` : `${theme.primary}15`,
                              color: c.severity === "CRITICAL" || c.severity === "HIGH" ? theme.danger : theme.primary,
                              fontWeight: 500,
                            }}>
                              {c.category}
                            </span>
                            <span style={{ fontSize: 11, color: theme.textSecondary, textTransform: "uppercase" }}>
                              {c.severity}
                            </span>
                          </div>
                          <p style={{ fontSize: 16, fontWeight: 500, color: theme.textPrimary, marginBottom: 4 }}>
                            {c.summary}
                          </p>
                          <p style={{ fontSize: 14, color: theme.textSecondary, lineHeight: 1.5 }}>
                            {c.rationale}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* ════ 9. Technical Details (collapsible) ════ */}
              <div>
                <button
                  onClick={() => setShowTechDetails(!showTechDetails)}
                  className="flex items-center gap-2 w-full py-3 px-4 rounded-2xl transition-colors"
                  style={{ background: theme.surface, border: `1px solid ${theme.border}`, color: theme.textSecondary, cursor: "pointer", fontSize: 14 }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                    style={{ transform: showTechDetails ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
                    <path d="m9 18 6-6-6-6" />
                  </svg>
                  Technical Details
                  <span style={{ marginLeft: "auto", color: theme.textSecondary, opacity: 0.6 }}>
                    {showTechDetails ? "collapse" : "expand"}
                  </span>
                </button>
                {showTechDetails && (
                  <div className="mt-4 space-y-6">
                    {/* Feature Vector */}
                    {data.feature_vector && (
                      <div>
                        <h4 style={{ fontSize: 14, color: theme.textSecondary, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                          Feature Vector  ·  v{data.feature_vector.schema_version}
                        </h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          {Object.entries(data.feature_vector.features).map(([key, val]) => (
                            <div key={key} className="py-1.5 px-2.5 rounded-lg" style={{ background: `${theme.primary}08`, border: `1px solid ${theme.border}` }}>
                              <div style={{ fontSize: 12, color: theme.textSecondary, marginBottom: 1 }}>{key.replace(/_/g, " ")}</div>
                              <div style={{ fontSize: 14, fontWeight: 600, color: theme.textPrimary }}>
                                {typeof val === "number" ? (val % 1 === 0 ? val : val.toFixed(3)) : String(val ?? "—")}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Evidence */}
                    {pipeline && pipeline.evidence.length > 0 && (
                      <div>
                        <h4 style={{ fontSize: 14, color: theme.textSecondary, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                          Evidence ({pipeline.evidence.length})
                        </h4>
                        <div className="space-y-2">
                          {pipeline.evidence.map((e) => (
                            <div key={e.id} className="py-2 px-3 rounded-lg" style={{ background: `${theme.primary}05`, border: `1px solid ${theme.border}` }}>
                              <div className="flex items-center gap-2 mb-0.5">
                                <span style={{ fontSize: 13, fontWeight: 500, color: theme.primary }}>{e.source_rule_id}</span>
                                <span style={{ fontSize: 12, color: theme.textSecondary }}>{(e.confidence * 100).toFixed(0)}%</span>
                              </div>
                              <p style={{ fontSize: 13, color: theme.textSecondary }}>{e.explanation}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Experiments */}
                    {pipeline && pipeline.experiments.length > 0 && (
                      <div>
                        <h4 style={{ fontSize: 14, color: theme.textSecondary, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                          Experiments ({pipeline.experiments.length})
                        </h4>
                        <div className="space-y-2">
                          {pipeline.experiments.map((e) => (
                            <div key={e.id} className="py-2 px-3 rounded-lg" style={{ background: `${theme.primary}05`, border: `1px solid ${theme.border}` }}>
                              <p style={{ fontSize: 14, color: theme.textPrimary, marginBottom: 2 }}>{e.hypothesis}</p>
                              <div className="flex gap-3">
                                {e.success_metric && <span style={{ fontSize: 12, color: theme.textSecondary }}>Metric: {e.success_metric}</span>}
                                <span style={{ fontSize: 12, textTransform: "uppercase", color: theme.primary }}>{e.status}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
              {/* What we analyzed */}
              {(data?.channel_metrics || pipeline) && (
                <div className="rounded-xl p-5" style={{ background: `${theme.textPrimary}03`, border: `1px solid ${theme.border}` }}>
                  <div style={{ fontSize: 13, color: theme.textSecondary, marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    What we analyzed
                  </div>
                  <div className="flex flex-wrap gap-x-6 gap-y-1.5 text-sm" style={{ color: theme.textSecondary }}>
                    {data.channel_metrics.total_videos != null && <span>{data.channel_metrics.total_videos} videos</span>}
                    {data.channel_metrics.total_views != null && <span>{formatCount(data.channel_metrics.total_views)} total views</span>}
                    {pipeline && pipeline.evidence.length > 0 && <span>{pipeline.evidence.length} evidence signals</span>}
                    {pipeline && pipeline.recommendations.length > 0 && <span>{pipeline.recommendations.length} experiments</span>}
                    {growthData?.score != null && <span>Growth Score: {growthData.score}/100</span>}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

function GrowthReviewCard({ theme, review: reviewData }: { theme: ThemeTokens; review: GrowthReviewData | null }) {
  if (!reviewData) {
    return null;
  }

  if (!reviewData.has_review) {
    return (
      <div className="rounded-2xl p-6" style={{ background: theme.surface, border: `1px solid ${theme.border}` }}>
        <div style={{ fontSize: 14, color: theme.textSecondary, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
          Growth Review
        </div>
        <div className="flex items-center gap-3" style={{ fontSize: 15, color: theme.textSecondary, lineHeight: 1.5 }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ flexShrink: 0 }}>
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4" />
            <path d="M12 8h.01" />
          </svg>
          {reviewData.message || "Complete an analysis to see your first Growth Review."}
        </div>
      </div>
    );
  }

  const fontSize = (px: number) => ({ fontSize: px, lineHeight: 1.7 });

  return (
    <div className="rounded-2xl p-6" style={{ background: theme.surface, border: `1px solid ${theme.border}` }}>
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: theme.primary, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>
            Growth Review
          </div>
          <div style={{ fontSize: 14, color: theme.textSecondary, opacity: 0.7 }}>
            Since your last analysis
          </div>
        </div>
        {reviewData.has_history && (
          <div className="flex items-center gap-1.5" style={{ fontSize: 12, color: theme.success, background: `${theme.success}12`, padding: "4px 10px", borderRadius: 8, fontWeight: 500 }}>
            Updated
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════
          ACT 1: Here's what happened
          ═══════════════════════════════════════════════════ */}
      <div className="mb-6">
        <ActLabel theme={theme} number={1} title="Here's what happened" />
        <p style={{ ...fontSize(16), color: theme.textPrimary }}>
          {reviewData.review}
        </p>
      </div>

      {/* ═══════════════════════════════════════════════════
          ACT 2: Here's why
          ═══════════════════════════════════════════════════ */}
      {(reviewData.evidence.strengths.length > 0 || reviewData.evidence.concerns.length > 0) && (
        <div className="mb-6">
          <ActLabel theme={theme} number={2} title="Why we think the strategy is working" />
          
          {reviewData.evidence.strengths.length > 0 && (
            <div className="space-y-2 mb-3">
              {reviewData.evidence.strengths.slice(0, 4).map((s, i) => (
                <div key={i} className="flex items-start gap-2.5 p-3 rounded-lg" style={{ background: `${theme.success}08`, border: `1px solid ${theme.success}18` }}>
                  <div style={{ color: theme.success, fontSize: 16, flexShrink: 0, marginTop: 1 }}>✓</div>
                  <div className="flex-1 min-w-0">
                    <div style={{ fontSize: 15, fontWeight: 600, color: theme.textPrimary, lineHeight: 1.4 }}>
                      {s.label}
                    </div>
                    {s.detail && (
                      <div style={{ fontSize: 13, color: theme.textSecondary, marginTop: 2, lineHeight: 1.4 }}>
                        {s.detail}
                      </div>
                    )}
                  </div>
                  {s.pct_change != null && (
                    <div className="flex-shrink-0" style={{
                      fontSize: 13, fontWeight: 600, padding: "1px 8px", borderRadius: 6, whiteSpace: "nowrap",
                      color: s.pct_change > 0 ? theme.success : theme.danger,
                      background: s.pct_change > 0 ? `${theme.success}15` : `${theme.danger}15`,
                    }}>
                      {s.pct_change > 0 ? "+" : ""}{s.pct_change}%
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {reviewData.evidence.concerns.length > 0 && (
            <div className="space-y-2">
              {reviewData.evidence.concerns.slice(0, 3).map((c, i) => {
                const isBad = c.severity === "high" || c.severity === "critical";
                return (
                  <div key={i} className="flex items-start gap-2.5 p-3 rounded-lg" style={{ background: isBad ? `${theme.danger}08` : `${theme.textPrimary}05`, border: `1px solid ${isBad ? `${theme.danger}18` : theme.border}` }}>
                    <div style={{ color: isBad ? theme.danger : "#f59e0b", fontSize: 16, flexShrink: 0, marginTop: 1 }}>⚠</div>
                    <div className="flex-1 min-w-0">
                      <div style={{ fontSize: 15, fontWeight: 600, color: theme.textPrimary, lineHeight: 1.4 }}>
                        {c.label}
                      </div>
                      {c.detail && (
                        <div style={{ fontSize: 13, color: theme.textSecondary, marginTop: 2, lineHeight: 1.4 }}>
                          {c.detail}
                        </div>
                      )}
                    </div>
                    {c.pct_change != null && (
                      <div className="flex-shrink-0" style={{
                        fontSize: 13, fontWeight: 600, padding: "1px 8px", borderRadius: 6, whiteSpace: "nowrap",
                        color: theme.danger,
                        background: `${theme.danger}15`,
                      }}>
                        {c.pct_change > 0 ? "+" : ""}{c.pct_change}%
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ═══════════════════════════════════════════════════
          ACT 3: Did our advice work?
          ═══════════════════════════════════════════════════ */}
      {reviewData.last_mission && (
        <div className="mb-6">
          <ActLabel theme={theme} number={3} title="Did our advice work?" />
          
          <div className="rounded-xl p-4" style={{ background: `${theme.primary}06`, border: `1px solid ${theme.border}` }}>
            {/* Mission description + status */}
            <div className="flex items-start justify-between gap-3 mb-3">
              <div style={{ fontSize: 15, color: theme.textPrimary, fontWeight: 500, fontStyle: "italic", lineHeight: 1.5, flex: 1 }}>
                "{reviewData.last_mission.description}"
              </div>
              <div style={{
                fontSize: 12, fontWeight: 600, padding: "3px 10px", borderRadius: 8, whiteSpace: "nowrap",
                color: reviewData.last_mission.status === "completed" ? theme.success :
                  reviewData.last_mission.status === "in_progress" ? "#f59e0b" : theme.textSecondary,
                background: reviewData.last_mission.status === "completed" ? `${theme.success}15` :
                  reviewData.last_mission.status === "in_progress" ? "rgba(245,158,11,0.12)" : `${theme.textSecondary}12`,
              }}>
                {reviewData.last_mission.status === "completed" ? "✅ Completed" :
                  reviewData.last_mission.status === "in_progress" ? "⏳ In progress" : "Not started"}
              </div>
            </div>

            {/* Outcome */}
            {reviewData.last_mission.outcome && (
              <div className="flex items-center gap-4 mb-3 p-3 rounded-lg" style={{ background: `${theme.background}`, border: `1px solid ${theme.border}` }}>
                <div className="text-center" style={{ minWidth: 60 }}>
                  <div style={{ fontSize: 11, color: theme.textSecondary, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 2 }}>
                    Before
                  </div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: theme.textPrimary, lineHeight: 1 }}>
                    {reviewData.last_mission.outcome.before.toLocaleString()}
                  </div>
                </div>
                <div style={{ fontSize: 16, color: theme.textSecondary, opacity: 0.4 }}>→</div>
                <div className="text-center" style={{ minWidth: 60 }}>
                  <div style={{ fontSize: 11, color: theme.textSecondary, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 2 }}>
                    After
                  </div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: theme.textPrimary, lineHeight: 1 }}>
                    {reviewData.last_mission.outcome.after.toLocaleString()}
                  </div>
                </div>
                <div style={{
                  fontSize: 13, fontWeight: 600, padding: "2px 8px", borderRadius: 6,
                  color: reviewData.last_mission.outcome.change_pct >= 0 ? theme.success : theme.danger,
                  background: reviewData.last_mission.outcome.change_pct >= 0 ? `${theme.success}15` : `${theme.danger}15`,
                }}>
                  {reviewData.last_mission.outcome.change_pct >= 0 ? "+" : ""}{reviewData.last_mission.outcome.change_pct}%
                </div>
                <div style={{ fontSize: 12, color: theme.textSecondary, marginLeft: "auto" }}>
                  {reviewData.last_mission.outcome.metric}
                </div>
              </div>
            )}

            {/* Verdict */}
            <div style={{ fontSize: 14, color: theme.textPrimary, fontWeight: 500, lineHeight: 1.5 }}>
              {reviewData.last_mission.verdict}
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════
          ACT 4: What we still don't know
          ═══════════════════════════════════════════════════ */}
      {reviewData.new_questions.length > 0 && (
        <div className="mb-6">
          <ActLabel theme={theme} number={4} title="What we still don't know" />
          <div className="space-y-3">
            {reviewData.new_questions.slice(0, 2).map((q, i) => (
              <div key={i} className="flex items-start gap-2.5 p-3 rounded-lg" style={{ background: `${theme.primary}06`, border: `1px solid ${theme.border}` }}>
                <span style={{ color: theme.primary, fontSize: 16, flexShrink: 0, marginTop: 1, fontWeight: 700 }}>?</span>
                <div>
                  <div style={{ fontSize: 14, color: theme.textPrimary, lineHeight: 1.6 }}>
                    {q}
                  </div>
                  <div style={{ fontSize: 12, color: theme.primary, marginTop: 4, fontWeight: 500 }}>
                    This question becomes the next experiment
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════
          ACT 5: What to do next
          ═══════════════════════════════════════════════════ */}
      {reviewData.next_focus && (
        <div>
          <ActLabel theme={theme} number={5} title="What to do next" />
          <div className="rounded-xl p-4" style={{ background: `${theme.primary}08`, border: `1px solid ${theme.primary}20` }}>
            <div style={{ fontSize: 16, fontWeight: 600, color: theme.primary, lineHeight: 1.5 }}>
              {reviewData.next_focus}
            </div>
            <div style={{ fontSize: 13, color: theme.textSecondary, marginTop: 6, lineHeight: 1.5 }}>
              Start this week. We'll measure the results in your next Growth Review.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ActLabel({ theme, number, title }: { theme: ThemeTokens; number: number; title: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div style={{
        width: 22, height: 22, borderRadius: "50%", flexShrink: 0,
        background: theme.primary, color: "#fff",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 12, fontWeight: 700,
      }}>
        {number}
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, color: theme.textPrimary }}>
        {title}
      </div>
    </div>
  );
}

function Card({ theme, children }: { theme: ThemeTokens; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl p-6" style={{ background: theme.surface, border: `1px solid ${theme.border}` }}>
      {children}
    </div>
  );
}

function MetricBox({ theme, label, value }: { theme: ThemeTokens; label: string; value: number | string | null | undefined }) {
  return (
    <div className="text-center">
      <div style={{ fontSize: 24, fontWeight: 700, color: theme.textPrimary, lineHeight: 1.2 }}>
        {value == null ? "—" : typeof value === "number" ? (
          value >= 1_000_000 ? `${(value / 1_000_000).toFixed(1)}M`
            : value >= 1_000 ? `${(value / 1_000).toFixed(1)}K`
            : value.toLocaleString()
        ) : value}
      </div>
      <div style={{ fontSize: 13, color: theme.textSecondary }}>{label}</div>
    </div>
  );
}

export default function AnalyticsPage() {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex min-h-screen items-center justify-center bg-background"><div className="animate-pulse w-12 h-12 rounded-full bg-white/5" /></div>;
  if (!user) return null;
  const avatarUrl = user.creator_profile?.thumbnail_url || user.user.avatar_url;
  return (
    <CreatorThemeProvider creatorId={user.user.id} avatarUrl={avatarUrl} bannerUrl={null} priority="avatar">
      <AnalyticsContent />
    </CreatorThemeProvider>
  );
}
