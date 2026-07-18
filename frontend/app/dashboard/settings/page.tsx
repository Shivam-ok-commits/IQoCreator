"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { CreatorThemeProvider } from "@/components/theme/CreatorThemeProvider";
import { useCreatorTheme } from "@/hooks/useCreatorTheme";
import { api } from "@/services/api";

function SettingsContent() {
  const { user, logout } = useAuth();
  const { theme } = useCreatorTheme();
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = useCallback(async () => {
    setLoggingOut(true);
    try {
      await logout();
    } catch {
      setLoggingOut(false);
    }
  }, [logout]);

  if (!user) return null;

  return (
    <main className="min-h-screen" style={{ background: theme.background }}>
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-6">
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

        <h1 className="font-display text-heading-2 mb-8" style={{ color: theme.textPrimary }}>Settings</h1>

        <div className="space-y-6">
          {/* Account */}
          <div className="rounded-2xl p-6" style={{ background: theme.surface, border: `1px solid ${theme.border}` }}>
            <h2 className="font-display text-heading-4 mb-4" style={{ color: theme.textPrimary }}>Account</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2">
                <span className="text-body" style={{ color: theme.textSecondary }}>Email</span>
                <span className="text-body" style={{ color: theme.textPrimary }}>{user.user.email}</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-body" style={{ color: theme.textSecondary }}>Display Name</span>
                <span className="text-body" style={{ color: theme.textPrimary }}>{user.user.display_name || "—"}</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-body" style={{ color: theme.textSecondary }}>Connected Provider</span>
                <span className="text-body" style={{ color: theme.textPrimary }}>{user.connected_account?.provider || "None"}</span>
              </div>
            </div>
          </div>

          {/* Channel */}
          {user.creator_profile && (
            <div className="rounded-2xl p-6" style={{ background: theme.surface, border: `1px solid ${theme.border}` }}>
              <h2 className="font-display text-heading-4 mb-4" style={{ color: theme.textPrimary }}>YouTube Channel</h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2">
                  <span className="text-body" style={{ color: theme.textSecondary }}>Name</span>
                  <span className="text-body" style={{ color: theme.textPrimary }}>{user.creator_profile.name || "—"}</span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-body" style={{ color: theme.textSecondary }}>Handle</span>
                  <span className="text-body" style={{ color: theme.textPrimary }}>{user.creator_profile.handle || "—"}</span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-body" style={{ color: theme.textSecondary }}>API Access</span>
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-small font-medium" style={{ background: user.connected_account?.has_token ? `${theme.success}15` : `${theme.danger}15`, color: user.connected_account?.has_token ? theme.success : theme.danger }}>
                    <span className="w-1.5 h-1.5 rounded-full bg-current" />
                    {user.connected_account?.has_token ? "Active" : "Inactive"}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Danger Zone */}
          <div className="rounded-2xl p-6" style={{ background: theme.surface, border: `1px solid ${theme.danger}20` }}>
            <h2 className="font-display text-heading-4 mb-4" style={{ color: theme.danger }}>Disconnect</h2>
            <p className="text-body mb-4" style={{ color: theme.textSecondary }}>
              Disconnect your account from IQoCreator. This will remove your session but
              preserve your imported data.
            </p>
            <button
              onClick={handleLogout}
              disabled={loggingOut}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-small font-medium transition-all duration-200"
              style={{
                color: theme.danger,
                background: `${theme.danger}10`,
                border: `1px solid ${theme.danger}25`,
                opacity: loggingOut ? 0.6 : 1,
              }}
            >
              {loggingOut ? "Disconnecting..." : "Disconnect Account"}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}

export default function SettingsPage() {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex min-h-screen items-center justify-center bg-background"><div className="animate-pulse w-12 h-12 rounded-full bg-white/5" /></div>;
  if (!user) return null;
  return (
    <CreatorThemeProvider creatorId={user.user.id} avatarUrl={user.creator_profile?.thumbnail_url || user.user.avatar_url} bannerUrl={null} priority="avatar">
      <SettingsContent />
    </CreatorThemeProvider>
  );
}
