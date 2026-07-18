"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { CreatorThemeProvider } from "@/components/theme/CreatorThemeProvider";
import { useCreatorTheme } from "@/hooks/useCreatorTheme";
import { CreatorHero } from "@/components/creator/CreatorHero";
import { api, type ImportStatus, type ImportResult } from "@/services/api";

interface DashboardCardData {
  title: string;
  description: string;
  href: string;
  delay: number;
  icon: React.ReactNode;
  comingSoon?: boolean;
}

const CARDS: DashboardCardData[] = [
  {
    title: "Growth Consultant",
    description: "Personalized growth score, bottlenecks, and recommended actions.",
    href: "/dashboard/analytics",
    delay: 0,
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="18" y1="20" x2="18" y2="10" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="6" y1="20" x2="6" y2="14" />
      </svg>
    ),
  },
  {
    title: "Content",
    description: "Browse your imported videos and their metadata.",
    href: "/dashboard/content",
    delay: 80,
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="4" width="20" height="16" rx="2" />
        <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
      </svg>
    ),
  },
  {
    title: "Research",
    description: "Discover trending topics and optimize your strategy.",
    href: "/dashboard/research",
    delay: 160,
    comingSoon: true,
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.3-4.3" />
      </svg>
    ),
  },
  {
    title: "Competitors",
    description: "Track similar creators and compare performance.",
    href: "/dashboard/competitors",
    delay: 240,
    comingSoon: true,
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    title: "Audience",
    description: "Understand your viewer demographics and behavior.",
    href: "/dashboard/audience",
    delay: 320,
    comingSoon: true,
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    title: "Settings",
    description: "Manage your account and connected services.",
    href: "/dashboard/settings",
    delay: 400,
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    ),
  },
];

function DashboardContent() {
  const { user, logout } = useAuth();
  const { theme } = useCreatorTheme();
  const [importStatus, setImportStatus] = useState<ImportStatus | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  const checkStatus = useCallback(async () => {
    try {
      const status = await api.getImportStatus();
      setImportStatus(status);
    } catch {
      /* not critical */
    }
  }, []);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  const handleImport = async () => {
    setImporting(true);
    setImportError(null);
    setImportResult(null);
    try {
      const result = await api.importChannel();
      setImportResult(result);
      if (result.success) {
        await checkStatus();
      }
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImporting(false);
    }
  };

  if (!user) return null;

  const profile = user.creator_profile;
  const hasImported = importStatus?.imported ?? false;
  const lastRun = importStatus?.runs?.[0] ?? null;

  return (
    <main
      className="min-h-screen"
      style={{ background: theme.background }}
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        <CreatorHero data={user} />

        <div className="mt-8">
          {!hasImported && !importResult && (
            <div
              className="rounded-2xl p-8 text-center"
              style={{
                background: theme.surface,
                border: `1px solid ${theme.border}`,
              }}
            >
              <h2
                className="font-display text-heading-3 mb-2"
                style={{ color: theme.textPrimary }}
              >
                Import Your Channel
              </h2>
              <p
                className="text-body mb-6"
                style={{ color: theme.textSecondary }}
              >
                Fetch your YouTube channel profile and current metrics.
              </p>
              <button
                onClick={handleImport}
                disabled={importing}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-base transition-all duration-200"
                style={{
                  background: theme.primary,
                  color: "#fff",
                  opacity: importing ? 0.6 : 1,
                }}
              >
                {importing ? (
                  <>
                    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="31.4 31.4" />
                    </svg>
                    Importing...
                  </>
                ) : (
                  "Import Channel"
                )}
              </button>
              {importError && (
                <p className="mt-4 text-caption" style={{ color: theme.danger }}>
                  {importError}
                </p>
              )}
            </div>
          )}

          {(hasImported || importResult?.success) && (
            <div
              className="rounded-2xl p-6"
              style={{
                background: theme.surface,
                border: `1px solid ${theme.border}`,
              }}
            >
              <div className="flex items-center gap-3 mb-4">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center"
                  style={{ background: `${theme.success}20` }}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={theme.success} strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
                <div>
                  <h3
                    className="font-display text-heading-4"
                    style={{ color: theme.textPrimary }}
                  >
                    Import Complete
                  </h3>
                  {lastRun?.completed_at && (
                    <p className="text-small" style={{ color: theme.textSecondary }}>
                      {new Date(lastRun.completed_at).toLocaleString()}
                    </p>
                  )}
                </div>
                <button
                  onClick={handleImport}
                  disabled={importing}
                  className="ml-auto px-4 py-2 rounded-xl text-small font-medium transition-all duration-200"
                  style={{
                    color: theme.primary,
                    background: `${theme.primary}10`,
                    border: `1px solid ${theme.primary}20`,
                    opacity: importing ? 0.6 : 1,
                  }}
                >
                  {importing ? "Importing..." : "Re-import"}
                </button>
              </div>
              {lastRun && (
                <div className="flex gap-6 text-center">
                  <div>
                    <p className="font-display text-heading-4" style={{ color: theme.textPrimary }}>
                      Channel
                    </p>
                    <p className="text-small" style={{ color: theme.textSecondary }}>
                      Profile
                    </p>
                  </div>
                  <div>
                    <p className="font-display text-heading-4" style={{ color: theme.textPrimary }}>
                      {lastRun.videos_imported}
                    </p>
                    <p className="text-small" style={{ color: theme.textSecondary }}>
                      Videos
                    </p>
                  </div>
                  <div>
                    <p className="font-display text-heading-4" style={{ color: lastRun.status === "completed" ? theme.success : theme.danger }}>
                      {lastRun.status === "completed" ? "Success" : lastRun.status}
                    </p>
                    <p className="text-small" style={{ color: theme.textSecondary }}>
                      Status
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {CARDS.map((card) => (
            <Link key={card.title} href={card.href} className="block">
              <DashboardCard
                title={card.title}
                description={card.description}
                delay={card.delay}
                icon={card.icon}
                comingSoon={card.comingSoon}
              />
            </Link>
          ))}
        </div>

        <div className="mt-8 flex justify-center pb-12">
          <button
            onClick={logout}
            className="px-5 py-2.5 rounded-xl text-caption font-medium transition-all duration-200"
            style={{
              color: theme.textSecondary,
              background: theme.surface,
              border: `1px solid ${theme.border}`,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = theme.danger;
              e.currentTarget.style.borderColor = `${theme.danger}40`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = theme.textSecondary;
              e.currentTarget.style.borderColor = theme.border;
            }}
          >
            Disconnect
          </button>
        </div>
      </div>
    </main>
  );
}

interface DashboardCardProps {
  title: string;
  description: string;
  delay: number;
  icon: React.ReactNode;
  comingSoon?: boolean;
}

function DashboardCard({ title, description, delay, icon, comingSoon }: DashboardCardProps) {
  const { theme } = useCreatorTheme();

  return (
    <div
      className="rounded-2xl p-6 relative cursor-pointer select-none"
      style={{
        background: theme.surface,
        border: `1px solid ${theme.border}`,
        animation: `fade-up 0.4s ease-out ${delay}ms forwards`,
        opacity: 0,
        transition: "border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease",
      }}
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
      {comingSoon && (
        <span
          className="absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider"
          style={{
            background: `${theme.primary}15`,
            color: theme.primary,
            border: `1px solid ${theme.primary}20`,
          }}
        >
          V2
        </span>
      )}
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center mb-3"
        style={{
          background: `${theme.primary}10`,
          color: theme.primary,
          border: `1px solid ${theme.primary}15`,
        }}
      >
        {icon}
      </div>
      <h3
        className="font-display text-heading-4 mb-1"
        style={{ color: theme.textPrimary }}
      >
        {title}
      </h3>
      <p
        className="text-caption"
        style={{ color: theme.textSecondary }}
      >
        {comingSoon ? `${description} Coming in V2.` : description}
      </p>
    </div>
  );
}

export default function DashboardPage() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-white/5" />
          <div className="w-40 h-4 rounded bg-white/5" />
        </div>
      </main>
    );
  }

  if (!user) return null;

  const profile = user.creator_profile;
  const avatarUrl = profile?.thumbnail_url || user.user.avatar_url;

  return (
    <CreatorThemeProvider
      creatorId={user.user.id}
      avatarUrl={avatarUrl}
      bannerUrl={null}
      priority="avatar"
    >
      <DashboardContent />
    </CreatorThemeProvider>
  );
}
