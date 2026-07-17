"use client";

import { useRef, useMemo, memo, useId } from "react";
import { motion, useMotionValue, useSpring, type MotionValue } from "framer-motion";
import { useCreatorTheme } from "@/hooks/useCreatorTheme";
import type { MeResponse } from "@/services/api";

function formatCount(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

interface ParticlesProps {
  count?: number;
}

const Particles = memo(function Particles({ count = 20 }: ParticlesProps) {
  const id = useId();
  const particles = useMemo(() => {
    return Array.from({ length: count }, (_, i) => ({
      id: `${id}-${i}`,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 2 + 1,
      duration: Math.random() * 30 + 25,
      delay: Math.random() * 10,
    }));
  }, [count, id]);

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden>
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute rounded-full bg-white"
          style={{
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
            opacity: 0.08,
          }}
          animate={{
            y: [0, -30, 0],
            opacity: [0.08, 0.15, 0.08],
          }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            ease: "linear",
            delay: p.delay,
          }}
        />
      ))}
    </div>
  );
});

interface RadialBlobProps {
  color: string;
  x: string;
  y: string;
  size: string;
  delay?: number;
}

const RadialBlob = memo(function RadialBlob({
  color,
  x,
  y,
  size,
  delay = 0,
}: RadialBlobProps) {
  return (
    <motion.div
      className="absolute rounded-full pointer-events-none"
      style={{
        left: x,
        top: y,
        width: size,
        height: size,
        background: `radial-gradient(circle, ${color} 0%, transparent 70%)`,
      }}
      animate={{
        scale: [1, 1.15, 1],
        opacity: [0.5, 0.7, 0.5],
      }}
      transition={{
        duration: 30,
        repeat: Infinity,
        ease: "easeInOut",
        delay,
      }}
    />
  );
});

interface ParallaxLayerProps {
  children: React.ReactNode;
  x: MotionValue<number>;
  y: MotionValue<number>;
  className?: string;
}

const ParallaxLayer = memo(function ParallaxLayer({
  children,
  x,
  y,
  className,
}: ParallaxLayerProps) {
  return (
    <motion.div
      className={className}
      style={{ x, y }}
    >
      {children}
    </motion.div>
  );
});

interface StatItemProps {
  label: string;
  value: string | number | null | undefined;
}

const StatItem = memo(function StatItem({ label, value }: StatItemProps) {
  const { theme } = useCreatorTheme();
  return (
    <div className="text-center">
      <p
        className="font-display text-heading-4 leading-none mb-1"
        style={{ color: theme.textPrimary }}
      >
        {formatCount(value === null || value === undefined ? null : Number(value))}
      </p>
      <p
        className="text-caption"
        style={{ color: theme.textSecondary }}
      >
        {label}
      </p>
    </div>
  );
});

interface CreatorHeroProps {
  data: MeResponse;
}

export function CreatorHero({ data }: CreatorHeroProps) {
  const { theme, loading } = useCreatorTheme();
  const containerRef = useRef<HTMLDivElement>(null);

  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const springX = useSpring(mouseX, { stiffness: 150, damping: 30 });
  const springY = useSpring(mouseY, { stiffness: 150, damping: 30 });

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = (e.clientX - cx) / rect.width;
    const dy = (e.clientY - cy) / rect.height;
    mouseX.set(dx * 10);
    mouseY.set(dy * 10);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  const profile = data.creator_profile;
  const metrics = data.channel_metrics;
  const channelName = profile?.name || data.user.display_name || "Creator";
  const channelHandle = profile?.handle
    ? profile.handle.startsWith("@")
      ? profile.handle
      : `@${profile.handle}`
    : null;
  const avatarUrl = profile?.thumbnail_url || data.user.avatar_url;
  const subscriberCount = metrics?.subscriber_count ?? profile?.subscriber_count;
  const totalViews = metrics?.total_views ?? profile?.total_views;
  const totalVideos = metrics?.total_videos;

  const particleCount = useMemo(() => {
    if (typeof window === "undefined") return 16;
    return window.innerWidth < 768 ? 8 : 16;
  }, []);

  return (
    <section
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="relative overflow-hidden rounded-3xl"
      style={{
        background: theme.background,
        minHeight: "clamp(280px, 20vh, 400px)",
      }}
    >
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: theme.radialGlow }}
      />

      <ParallaxLayer x={springX} y={springY} className="absolute inset-0">
        <RadialBlob
          color={theme.glow}
          x="10%"
          y="-10%"
          size="60%"
          delay={0}
        />
        <RadialBlob
          color={theme.glow}
          x="60%"
          y="30%"
          size="50%"
          delay={10}
        />
        <RadialBlob
          color={theme.glow}
          x="30%"
          y="50%"
          size="40%"
          delay={20}
        />
      </ParallaxLayer>

      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `linear-gradient(180deg, transparent 50%, ${theme.background} 100%)`,
        }}
      />

      <Particles count={particleCount} />

      <div className="absolute inset-0 pointer-events-none bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzMDAiIGhlaWdodD0iMzAwIj48ZmlsdGVyIGlkPSJmIj48ZmVUdXJidWxlbmNlIHR5cGU9ImZyYWN0YWxOb2lzZSIgYmFzZUZyZXF1ZW5jeT0iLjc1IiBudW1PY3RhdmVzPSIzIi8+PC9maWx0ZXI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgb3BhY2l0eT0iMC4wMiIgZmlsdGVyPSJ1cmwoI2YpIi8+PC9zdmc+')] opacity-30" />

      <div className="relative z-10 px-6 py-8 md:px-10 md:py-10 lg:px-14 lg:py-12">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="flex flex-col md:flex-row md:items-center gap-6 md:gap-10"
        >
          <div className="shrink-0 flex items-start gap-4">
            <div className="relative">
              <div className="w-16 h-16 md:w-20 md:h-20 lg:w-24 lg:h-24 rounded-full overflow-hidden"
                style={{
                  outline: `2px solid ${theme.border}`,
                  outlineOffset: "2px",
                }}
              >
                {avatarUrl ? (
                  <img
                    src={avatarUrl}
                    alt={channelName}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div
                    className="w-full h-full flex items-center justify-center font-display text-heading-3"
                    style={{ background: theme.surface, color: theme.textSecondary }}
                  >
                    {channelName.charAt(0).toUpperCase()}
                  </div>
                )}
              </div>
              <div
                className="absolute -bottom-0.5 -right-0.5 w-5 h-5 rounded-full flex items-center justify-center"
                style={{ background: theme.success }}
              >
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
            </div>

            <div className="md:hidden">
              <div className="flex items-center gap-2">
                <h1
                  className="font-display text-heading-3 leading-tight"
                  style={{ color: theme.textPrimary }}
                >
                  {channelName}
                </h1>
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="#1d9bf0"
                  className="shrink-0 mt-0.5"
                >
                  <path d="M22.5 12.5c0-1.58-.875-2.95-2.148-3.6.154-.435.238-.905.238-1.4 0-2.21-1.71-3.998-3.818-3.998-.47 0-.92.084-1.336.25C14.818 2.415 13.043 1.5 11.045 1.5c-1.615 0-3.07.69-4.083 1.79-.535-.12-1.095-.19-1.672-.19-2.345 0-4.29 1.95-4.29 4.36 0 .38.04.75.12 1.1C1.57 8.9 1 9.9 1 11c0 2.29 1.88 4.15 4.21 4.15.17 0 .33-.01.5-.02.56.38 1.12.61 1.73.79-.16.69-.26 1.42-.26 2.18 0 .29.02.58.05.86C6.36 20.32 8.35 21 10.55 21c4.6 0 8.33-2.13 8.33-5.24 0-.35-.04-.68-.1-1 .79-.4 1.47-1 1.98-1.73.4.05.8.07 1.22.07 2.07 0 3.52-1.15 3.52-2.7z" />
                </svg>
              </div>
              {channelHandle && (
                <p
                  className="text-caption mt-0.5"
                  style={{ color: theme.textSecondary }}
                >
                  {channelHandle}
                </p>
              )}
            </div>
          </div>

          <div className="flex-1 min-w-0 hidden md:block">
            <div className="flex items-center gap-2">
              <h1
                className="font-display text-heading-2 lg:text-heading-1 leading-tight truncate"
                style={{ color: theme.textPrimary }}
              >
                {channelName}
              </h1>
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="#1d9bf0"
                className="shrink-0 mt-1"
              >
                <path d="M22.5 12.5c0-1.58-.875-2.95-2.148-3.6.154-.435.238-.905.238-1.4 0-2.21-1.71-3.998-3.818-3.998-.47 0-.92.084-1.336.25C14.818 2.415 13.043 1.5 11.045 1.5c-1.615 0-3.07.69-4.083 1.79-.535-.12-1.095-.19-1.672-.19-2.345 0-4.29 1.95-4.29 4.36 0 .38.04.75.12 1.1C1.57 8.9 1 9.9 1 11c0 2.29 1.88 4.15 4.21 4.15.17 0 .33-.01.5-.02.56.38 1.12.61 1.73.79-.16.69-.26 1.42-.26 2.18 0 .29.02.58.05.86C6.36 20.32 8.35 21 10.55 21c4.6 0 8.33-2.13 8.33-5.24 0-.35-.04-.68-.1-1 .79-.4 1.47-1 1.98-1.73.4.05.8.07 1.22.07 2.07 0 3.52-1.15 3.52-2.7z" />
              </svg>
            </div>
            {channelHandle && (
              <p
                className="text-body mt-0.5"
                style={{ color: theme.textSecondary }}
              >
                {channelHandle}
              </p>
            )}
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, delay: 0.15 }}
            className="shrink-0 ml-auto"
          >
            <div
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-small font-medium"
              style={{
                background: `${theme.success}15`,
                color: theme.success,
                border: `1px solid ${theme.success}25`,
              }}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-current" />
              Connected
            </div>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="mt-6 md:mt-8"
        >
          <div
            className="inline-grid grid-cols-4 divide-x rounded-2xl px-6 py-4"
            style={{
              background: theme.surface,
              border: `1px solid ${theme.border}`,
            }}
          >
            <StatItem label="Subscribers" value={subscriberCount} />
            <StatItem label="Views" value={totalViews} />
            <StatItem label="Videos" value={totalVideos} />
            <StatItem label="Uploads/mo" value={null} />
          </div>
        </motion.div>
      </div>
    </section>
  );
}
