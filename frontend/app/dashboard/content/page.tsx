"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { CreatorThemeProvider } from "@/components/theme/CreatorThemeProvider";
import { useCreatorTheme } from "@/hooks/useCreatorTheme";
import { CreatorHero } from "@/components/creator/CreatorHero";
import { api, type VideosResponse } from "@/services/api";

function ContentPage() {
  const { user } = useAuth();
  const { theme } = useCreatorTheme();
  const [data, setData] = useState<VideosResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const videos = await api.getVideos();
        setData(videos);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load videos");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (!user) return null;

  return (
    <main className="min-h-screen" style={{ background: theme.background }}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        <div className="mb-6">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 text-caption transition-colors"
            style={{ color: theme.textSecondary }}
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
          <h1 className="font-display text-heading-2 mb-6" style={{ color: theme.textPrimary }}>
            Content
            {data && <span className="ml-2 text-body font-normal" style={{ color: theme.textSecondary }}>{data.total} videos</span>}
          </h1>

          {loading && (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin w-8 h-8 rounded-full border-2" style={{ borderColor: `${theme.primary}30`, borderTopColor: theme.primary }} />
            </div>
          )}

          {error && (
            <div className="rounded-2xl p-8 text-center" style={{ background: theme.surface, border: `1px solid ${theme.border}` }}>
              <p style={{ color: theme.danger }}>{error}</p>
            </div>
          )}

          {data && data.videos.length === 0 && (
            <div className="rounded-2xl p-12 text-center" style={{ background: theme.surface, border: `1px solid ${theme.border}` }}>
              <p className="text-body" style={{ color: theme.textSecondary }}>No videos imported yet. Import your channel first.</p>
            </div>
          )}

          {data && data.videos.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.videos.map((video) => (
                <a
                  key={video.id}
                  href={video.url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-2xl overflow-hidden transition-all duration-200"
                  style={{ background: theme.surface, border: `1px solid ${theme.border}`, display: "block" }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = `${theme.primary}30`;
                    e.currentTarget.style.boxShadow = `0 0 30px -10px ${theme.glow}`;
                    e.currentTarget.style.transform = "scale(1.02)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = theme.border;
                    e.currentTarget.style.boxShadow = "none";
                    e.currentTarget.style.transform = "scale(1)";
                  }}
                >
                  {video.thumbnail_url && (
                    <div className="aspect-video bg-black/40 overflow-hidden">
                      <img
                        src={video.thumbnail_url}
                        alt={video.title}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    </div>
                  )}
                  <div className="p-4">
                    <h3 className="font-display text-heading-4 mb-1 line-clamp-2" style={{ color: theme.textPrimary }}>
                      {video.title}
                    </h3>
                    {video.published_at && (
                      <p className="text-small" style={{ color: theme.textSecondary }}>
                        {new Date(video.published_at).toLocaleDateString()}
                        {video.duration_seconds && ` · ${Math.floor(video.duration_seconds / 60)}:${(video.duration_seconds % 60).toString().padStart(2, "0")}`}
                      </p>
                    )}
                  </div>
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

export default function ContentWrapper() {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex min-h-screen items-center justify-center bg-background"><div className="animate-pulse w-12 h-12 rounded-full bg-white/5" /></div>;
  if (!user) return null;
  const avatarUrl = user.creator_profile?.thumbnail_url || user.user.avatar_url;
  return (
    <CreatorThemeProvider creatorId={user.user.id} avatarUrl={avatarUrl} bannerUrl={null} priority="avatar">
      <ContentPage />
    </CreatorThemeProvider>
  );
}
