"use client";

import { useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";

export default function Home() {
  const { user, loading, isAuthenticated, login, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.push("/connected");
    }
  }, [loading, isAuthenticated, router]);

  if (loading) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-background">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-white/5" />
          <div className="w-48 h-4 rounded bg-white/5" />
        </div>
      </main>
    );
  }

  if (isAuthenticated) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-background">
        <div className="animate-fade-up text-center space-y-6">
          <p className="text-foreground/60">Redirecting...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(217,4,41,0.08),transparent_60%)] pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center text-center px-6 max-w-3xl mx-auto">
        <div className="animate-fade-up mb-4">
          <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/5 bg-white/[0.02] text-caption text-foreground/50">
            <span className="w-1.5 h-1.5 rounded-full bg-crimson-500 animate-pulse" />
            AI-Powered Research Platform
          </span>
        </div>

        <h1 className="animate-in-delay-1 font-display text-display-1 md:text-[120px] leading-[0.85] tracking-[-0.04em] text-foreground mb-6">
          IQoCreator
        </h1>

        <p className="animate-in-delay-2 text-body md:text-xl text-foreground/50 max-w-xl mb-12 leading-relaxed">
          Transform your YouTube strategy with deterministic,
          explainable recommendations powered by deep content analysis.
        </p>

        <div className="animate-in-delay-3 flex flex-col sm:flex-row items-center gap-4">
          <button
            onClick={login}
            className="btn-primary text-base px-10 py-5 rounded-xl gap-3"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M15.22 6.55a5.5 5.5 0 0 1 3.77 1.73 5.5 5.5 0 0 1 0 7.44" />
              <path d="M18.36 3.64a9 9 0 0 1 2.31 10.18" />
              <path d="M10.29 20.69a7 7 0 0 1-2.9-3.5" />
              <path d="M6.27 6.27a7 7 0 0 1 3.9-2.9" />
              <path d="M12 2v2" />
              <path d="M13.5 7.5 9 12l4 4 4.5-4.5" />
              <path d="M12 22v-2" />
            </svg>
            Connect YouTube Account
          </button>
        </div>

        <div className="animate-in-delay-3 mt-16 grid grid-cols-3 gap-12 text-center">
          <div className="space-y-2">
            <p className="font-display text-heading-2 text-foreground">3</p>
            <p className="text-caption text-foreground/40">Data Points</p>
          </div>
          <div className="space-y-2">
            <p className="font-display text-heading-2 text-foreground">0</p>
            <p className="text-caption text-foreground/40">Videos Analyzed</p>
          </div>
          <div className="space-y-2">
            <p className="font-display text-heading-2 text-foreground">0</p>
            <p className="text-caption text-foreground/40">Recommendations</p>
          </div>
        </div>
      </div>

      <footer className="absolute bottom-8 text-center w-full">
        <p className="text-small text-foreground/20">
          IQoCreator &mdash; v0.1.0
        </p>
      </footer>
    </main>
  );
}
