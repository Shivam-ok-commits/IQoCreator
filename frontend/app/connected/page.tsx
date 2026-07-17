"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";

export default function ConnectedPage() {
  const { user, loading, isAuthenticated, logout, checkSession } = useAuth();
  const router = useRouter();
  const [errorParams, setErrorParams] = useState<string | null>(null);
  const [navigating, setNavigating] = useState(false);

  const handleImport = useCallback(() => {
    if (navigating) return;
    setNavigating(true);
    router.push("/importing");
  }, [navigating, router]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const err = params.get("error");
    if (err) {
      setErrorParams(err);
    }
  }, []);

  useEffect(() => {
    if (!loading && !isAuthenticated && !errorParams) {
      router.push("/");
    }
  }, [loading, isAuthenticated, router, errorParams]);

  if (loading) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-background">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-white/5" />
          <div className="w-56 h-5 rounded bg-white/5" />
          <div className="w-32 h-4 rounded bg-white/5" />
        </div>
      </main>
    );
  }

  if (errorParams) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-background">
        <div className="flex flex-col items-center text-center max-w-md px-6 space-y-6">
          <div className="w-16 h-16 rounded-2xl bg-crimson-500/10 border border-crimson-500/20 flex items-center justify-center">
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-crimson-400"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h1 className="font-display text-heading-2 text-foreground">
            Connection Failed
          </h1>
          <p className="text-body text-foreground/50">
            {errorParams === "invalid_state" &&
              "Invalid OAuth state. Please try again."}
            {errorParams === "missing_code" &&
              "No authorization code received."}
            {errorParams === "no_token" &&
              "Failed to obtain access token from Google."}
            {errorParams === "no_subject" &&
              "Could not verify your Google identity."}
            {!["invalid_state", "missing_code", "no_token", "no_subject"].includes(errorParams) &&
              "An unexpected error occurred."}
          </p>
          <button
            onClick={() => router.push("/")}
            className="btn-primary"
          >
            Try Again
          </button>
        </div>
      </main>
    );
  }

  if (!user) {
    return null;
  }

  const channelName = user.creator_profile?.name || "YouTube Creator";
  const channelAvatar =
    user.creator_profile?.thumbnail_url || user.user.avatar_url;
  const subscriberCount = user.channel_metrics?.subscriber_count ?? user.creator_profile?.subscriber_count;

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_-10%,rgba(217,4,41,0.06),transparent_50%)] pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center text-center px-6 max-w-lg mx-auto">
        <div className="animate-scale-in mb-8">
          <div className="w-20 h-20 rounded-2xl bg-crimson-500/10 border border-crimson-500/20 flex items-center justify-center glow-red">
            <svg
              width="36"
              height="36"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-crimson-400"
            >
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          </div>
        </div>

        <div className="animate-fade-up space-y-3 mb-10">
          <h1 className="font-display text-display-3 text-foreground leading-[0.9]">
            Connected
          </h1>
          <p className="text-body text-foreground/40">
            Your YouTube account has been linked successfully.
          </p>
        </div>

        <div className="animate-in-delay-1 w-full card-premium p-6 rounded-2xl space-y-5">
          {channelAvatar && (
            <div className="flex justify-center">
              <div className="w-20 h-20 rounded-full overflow-hidden ring-2 ring-crimson-500/20">
                <img
                  src={channelAvatar}
                  alt={channelName}
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          )}

          <div className="text-center space-y-2">
            <p className="font-display text-heading-3 text-foreground">
              {channelName}
            </p>
            {user.creator_profile?.handle && (
              <p className="text-body text-foreground/50">
                @{user.creator_profile.handle.replace("@", "")}
              </p>
            )}
          </div>

          <div className="flex items-center justify-center gap-3 py-3 px-4 rounded-xl bg-white/[0.03] border border-white/5">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-foreground/40 shrink-0"
            >
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
            </svg>
            <span className="text-caption text-foreground/50">
              {user.user.email}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="py-3 px-4 rounded-xl bg-white/[0.03] border border-white/5 text-center">
              <p className="font-display text-heading-4 text-foreground">
                {subscriberCount?.toLocaleString() || "—"}
              </p>
              <p className="text-small text-foreground/40">Subscribers</p>
            </div>
            <div className="py-3 px-4 rounded-xl bg-white/[0.03] border border-white/5 text-center">
              <p className="font-display text-heading-4 text-foreground">
                {user.connected_account?.has_token ? "Active" : "—"}
              </p>
              <p className="text-small text-foreground/40">API Access</p>
            </div>
          </div>
        </div>

        <div className="animate-in-delay-2 mt-10 flex flex-col sm:flex-row items-center gap-4">
          <button
            onClick={handleImport}
            disabled={navigating}
            className="btn-primary"
          >
            Import Channel
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
          </button>
          <button
            onClick={logout}
            className="btn-ghost text-crimson-400/60 hover:text-crimson-400"
          >
            Disconnect
          </button>
        </div>
      </div>
    </main>
  );
}
