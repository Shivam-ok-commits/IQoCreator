const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_URL}${endpoint}`;
  const { headers, ...rest } = options ?? {};
  const res = await fetch(url, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    ...rest,
  });

  if (res.status === 401) {
    throw new ApiError(401, "Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || "Request failed");
  }

  if (res.headers.get("content-type")?.includes("application/json")) {
    return res.json();
  }

  return {} as T;
}

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
}

export interface CreatorProfile {
  name: string | null;
  handle: string | null;
  thumbnail_url: string | null;
  subscriber_count: number | null;
  total_views: number | null;
}

export interface ChannelMetricsData {
  subscriber_count: number | null;
  total_views: number | null;
  total_videos: number | null;
}

export interface MeResponse {
  user: User;
  connected_account: { provider: string | null; has_token: boolean };
  creator_profile: CreatorProfile | null;
  channel_metrics: ChannelMetricsData | null;
}

export interface ImportResult {
  success: boolean;
  imported: number;
  updated: number;
  duration_ms: number;
  error: string | null;
}

export interface ImportRunInfo {
  id: string;
  status: string;
  videos_imported: number;
  videos_failed: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface ImportStatus {
  imported: boolean;
  last_imported_at: string | null;
  runs: ImportRunInfo[];
}

export interface AnalyticsSummary {
  channel_metrics: {
    subscriber_count: number | null;
    total_views: number | null;
    total_videos: number | null;
  };
  metric_snapshot: {
    snapshot_at: string | null;
    total_videos: number | null;
    total_views: number | null;
    total_subscribers: number | null;
    engagement_rate: number | null;
  } | null;
  feature_vector: {
    computed_at: string | null;
    features: Record<string, unknown>;
    schema_version: number | null;
  } | null;
  findings: {
    total: number;
    high_severity: number;
    critical_severity: number;
    items: Array<{
      rule_id: string;
      severity: string;
      category: string;
      title: string;
      description: string;
    }>;
  };
}

export interface IntelligencePattern {
  id: string;
  type: string;
  summary: string;
  explanation: string | null;
  confidence: number;
  impact: number;
  impact_score: number;
  metrics: Record<string, unknown>;
  evidence: Record<string, unknown>;
  suggested_actions: string[];
}

export interface GrowthScoreData {
  score: number | null;
  tier: string | null;
  summary: string | null;
  potential_low: number | null;
  potential_high: number | null;
  previous_score: number | null;
  delta: number | null;
  recorded_at: string | null;
}

export interface VideoItem {
  id: string;
  title: string;
  thumbnail_url: string | null;
  published_at: string | null;
  duration_seconds: number | null;
  url: string | null;
  platform_video_id: string;
  view_count?: number | null;
  like_count?: number | null;
  comment_count?: number | null;
}

export interface VideosResponse {
  videos: VideoItem[];
  total: number;
}

export interface GrowthReviewData {
  has_review: boolean;
  message?: string;
  has_history?: boolean;
  // Act 1: Executive review
  review: string;
  // Act 2: Why we believe this
  evidence: {
    strengths: Array<{
      label: string;
      detail: string;
      pct_change?: number | null;
      category: string;
    }>;
    concerns: Array<{
      label: string;
      detail: string;
      pct_change?: number | null;
      category: string;
      severity: string;
    }>;
  };
  // Act 3: Did our advice work?
  last_mission: {
    description: string;
    status: string;
    outcome: {
      metric: string;
      before: number;
      after: number;
      change_pct: number;
    } | null;
    verdict: string;
    verdict_enum: string;
  } | null;
  // Act 4: What we still don't know
  new_questions: string[];
  // Act 5: What to do next
  next_focus: string;
}

export const api = {
  me: () => request<MeResponse>("/api/auth/me"),

  logout: () =>
    request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),

  login: () => {
    window.location.href = `${API_URL}/api/auth/login`;
  },

  importChannel: () =>
    request<ImportResult>("/api/import/channel", { method: "POST" }),

  getImportStatus: () =>
    request<ImportStatus>("/api/import/status"),

  getAnalyticsSummary: () =>
    request<AnalyticsSummary>("/api/analytics/summary"),

  getPipeline: () =>
    request<{
      evidence: Array<{
        id: string;
        source_rule_id: string;
        confidence: number;
        explanation: string;
      }>;
      claims: Array<{
        id: string;
        category: string;
        severity: string;
        summary: string;
        rationale: string;
      }>;
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
      experiments: Array<{
        id: string;
        hypothesis: string;
        status: string;
        success_metric: string;
      }>;
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
    }>("/api/analytics/pipeline"),

  getVideos: () => request<VideosResponse>("/api/analytics/videos"),

  getGrowth: () => request<GrowthScoreData>("/api/analytics/growth"),

  getGrowthReview: () =>
    request<GrowthReviewData>("/api/analytics/review"),

  getPatterns: () =>
    request<{ patterns: IntelligencePattern[]; total: number }>("/api/analytics/patterns"),
};
