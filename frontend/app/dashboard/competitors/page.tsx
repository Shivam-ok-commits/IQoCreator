"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { CreatorThemeProvider } from "@/components/theme/CreatorThemeProvider";
import { useCreatorTheme } from "@/hooks/useCreatorTheme";

function CompetitorsContent() {
  const { user } = useAuth();
  const { theme } = useCreatorTheme();
  if (!user) return null;

  return (
    <main className="min-h-screen" style={{ background: theme.background }}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
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
        <div className="flex flex-col items-center justify-center py-32 text-center">
          <div className="w-16 h-16 rounded-2xl mb-6 flex items-center justify-center" style={{ background: `${theme.primary}10`, border: `1px solid ${theme.primary}20` }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: theme.primary }}>
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <h1 className="font-display text-heading-2 mb-3" style={{ color: theme.textPrimary }}>Competitor Analysis</h1>
          <p className="text-body max-w-md" style={{ color: theme.textSecondary }}>
            Competitor analysis coming in V2. This will help you track similar creators
            and compare performance in your niche.
          </p>
        </div>
      </div>
    </main>
  );
}

export default function CompetitorsPage() {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex min-h-screen items-center justify-center bg-background"><div className="animate-pulse w-12 h-12 rounded-full bg-white/5" /></div>;
  if (!user) return null;
  return (
    <CreatorThemeProvider creatorId={user.user.id} avatarUrl={user.creator_profile?.thumbnail_url || user.user.avatar_url} bannerUrl={null} priority="avatar">
      <CompetitorsContent />
    </CreatorThemeProvider>
  );
}
