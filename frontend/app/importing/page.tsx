"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { api, type ImportResult } from "@/services/api";

type ImportStage = "connecting" | "fetching" | "saving" | "complete" | "error";

interface StageConfig {
  key: ImportStage;
  label: string;
}

const STAGES: StageConfig[] = [
  { key: "connecting", label: "Connecting..." },
  { key: "fetching", label: "Fetching Channel..." },
  { key: "saving", label: "Saving..." },
  { key: "complete", label: "Complete" },
];

const STAGE_ORDER: ImportStage[] = ["connecting", "fetching", "saving", "complete"];

function stageIndex(stage: ImportStage): number {
  const idx = STAGE_ORDER.indexOf(stage);
  return idx >= 0 ? idx : 0;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatCount(n: number | null | undefined): string {
  if (n == null) return "\u2014";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

export default function ImportingPage() {
  const { user, loading, isAuthenticated, checkSession } = useAuth();
  const router = useRouter();
  const [stage, setStage] = useState<ImportStage>("connecting");
  const [result, setResult] = useState<ImportResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastImported, setLastImported] = useState<string | null>(null);
  const importingRef = useRef(false);

  const doImport = useCallback(async () => {
    if (importingRef.current) return;
    importingRef.current = true;

    setStage("connecting");
    setErrorMessage(null);
    setResult(null);

    await new Promise((r) => setTimeout(r, 200));

    try {
      setStage("fetching");
      const res = await api.importChannel();
      setResult(res);

      if (!res.success) {
        setStage("error");
        setErrorMessage(res.error || "Import failed");
        importingRef.current = false;
        return;
      }

      setStage("saving");
      await checkSession();

      setStage("complete");

      try {
        const status = await api.getImportStatus();
        if (status.last_imported_at) {
          setLastImported(new Date(status.last_imported_at).toLocaleString());
        }
      } catch {
        // non-critical
      }
    } catch (err) {
      setStage("error");
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("An unexpected error occurred");
      }
    } finally {
      importingRef.current = false;
    }
  }, [checkSession]);

  useEffect(() => {
    if (loading) return;
    if (!isAuthenticated) {
      router.push("/");
      return;
    }
    doImport();
  }, [loading, isAuthenticated, doImport, router]);

  if (loading) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-background">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-white/5" />
          <div className="w-40 h-4 rounded bg-white/5" />
        </div>
      </main>
    );
  }

  if (!user) return null;

  const currentIdx = stageIndex(stage);
  const profile = user.creator_profile;
  const metrics = user.channel_metrics;

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_-10%,rgba(217,4,41,0.06),transparent_50%)] pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center text-center px-6 max-w-lg mx-auto w-full">
        {stage === "error" && (
          <div className="w-full animate-fade-up">
            <div className="mb-8">
              <div className="w-16 h-16 rounded-2xl bg-crimson-500/10 border border-crimson-500/20 flex items-center justify-center mx-auto">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-crimson-400">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>
            </div>

            <h1 className="font-display text-display-3 text-foreground leading-[0.9] mb-3">
              Import Failed
            </h1>

            <div className="card-premium p-6 rounded-2xl mb-8">
              <p className="text-body text-foreground/60">
                {errorMessage || "Unable to complete the import. Please try again."}
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-4 justify-center">
              <button onClick={doImport} className="btn-primary">
                Retry Import
              </button>
              <button onClick={() => router.push("/connected")} className="btn-ghost">
                Back
              </button>
            </div>
          </div>
        )}

        {(stage === "connecting" || stage === "fetching" || stage === "saving") && (
          <div className="w-full animate-fade-up">
            <div className="mb-8">
              <div className="w-16 h-16 rounded-2xl bg-crimson-500/10 border border-crimson-500/20 flex items-center justify-center mx-auto glow-red">
                <svg className="animate-spin w-7 h-7 text-crimson-400" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="31.4 31.4" />
                </svg>
              </div>
            </div>

            <h1 className="font-display text-display-3 text-foreground leading-[0.9] mb-10">
              Importing Channel
            </h1>

            <div className="card-premium p-6 rounded-2xl mb-8">
              <div className="space-y-4">
                {STAGES.filter((s) => s.key !== "complete").map((s, i) => {
                  const isActive = i === currentIdx;
                  const isDone = i < currentIdx;
                  return (
                    <div key={s.key} className="flex items-center gap-4">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-all duration-300 ${
                        isDone ? "bg-crimson-500" : isActive ? "bg-crimson-500/20 border border-crimson-500/40" : "bg-white/5 border border-white/10"
                      }`}>
                        {isDone ? (
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        ) : isActive ? (
                          <div className="w-2 h-2 rounded-full bg-crimson-400 animate-pulse" />
                        ) : null}
                      </div>
                      <span className={`text-body transition-all duration-300 ${
                        isDone ? "text-foreground/80" : isActive ? "text-foreground font-medium" : "text-foreground/30"
                      }`}>
                        {s.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {stage === "complete" && result && (
          <div className="w-full animate-fade-up">
            <div className="mb-8">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2.5">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
            </div>

            <h1 className="font-display text-display-3 text-foreground leading-[0.9] mb-2">
              Channel Imported
            </h1>

            <div className="card-premium p-6 rounded-2xl space-y-5 mb-8">
              {profile?.thumbnail_url && (
                <div className="flex justify-center">
                  <div className="w-20 h-20 rounded-full overflow-hidden ring-2 ring-emerald-500/20">
                    <img src={profile.thumbnail_url} alt={profile.name || ""} className="w-full h-full object-cover" />
                  </div>
                </div>
              )}

              <div className="text-center space-y-1">
                <p className="font-display text-heading-3 text-foreground">
                  {profile?.name || "YouTube Channel"}
                </p>
                {profile?.handle && (
                  <p className="text-body text-foreground/50">
                    @{profile.handle.replace("@", "")}
                  </p>
                )}
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="py-3 px-2 rounded-xl bg-white/[0.03] border border-white/5 text-center">
                  <p className="font-display text-heading-4 text-foreground">
                    {formatCount(metrics?.subscriber_count ?? profile?.subscriber_count)}
                  </p>
                  <p className="text-small text-foreground/40">Subscribers</p>
                </div>
                <div className="py-3 px-2 rounded-xl bg-white/[0.03] border border-white/5 text-center">
                  <p className="font-display text-heading-4 text-foreground">
                    {formatCount(metrics?.total_views ?? profile?.total_views ?? null)}
                  </p>
                  <p className="text-small text-foreground/40">Views</p>
                </div>
                <div className="py-3 px-2 rounded-xl bg-white/[0.03] border border-white/5 text-center">
                  <p className="font-display text-heading-4 text-foreground">
                    {formatCount(metrics?.total_videos ?? null)}
                  </p>
                  <p className="text-small text-foreground/40">Videos</p>
                </div>
              </div>

              <div className="flex items-center justify-center gap-6 py-3 px-4 rounded-xl bg-white/[0.03] border border-white/5">
                <div className="text-center">
                  <p className="text-caption text-foreground/40">Duration</p>
                  <p className="text-caption text-foreground/70 font-medium">
                    {formatDuration(result.duration_ms)}
                  </p>
                </div>
                {lastImported && (
                  <div className="text-center">
                    <p className="text-caption text-foreground/40">Last Imported</p>
                    <p className="text-caption text-foreground/70 font-medium">
                      {lastImported}
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-4 justify-center">
              <button onClick={() => router.push("/dashboard")} className="btn-primary">
                Continue to Dashboard
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
              </button>
              <button onClick={doImport} className="btn-ghost">
                Import Again
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
