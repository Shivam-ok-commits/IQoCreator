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
  const res = await fetch(url, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
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
};
