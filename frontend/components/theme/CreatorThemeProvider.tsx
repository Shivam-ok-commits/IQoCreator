"use client";

import { createContext, useCallback, useEffect, useState, useRef } from "react";
import { extractDominantColors } from "./ColorExtractor";
import { generateTheme, generateFallbackTheme } from "./ThemeGenerator";
import { ThemeTokens, FALLBACK_THEME } from "./ThemeTokens";
import { ThemeCache } from "./ThemeCache";

interface CreatorThemeContextValue {
  theme: ThemeTokens;
  loading: boolean;
  error: boolean;
  refresh: () => void;
}

export const CreatorThemeContext = createContext<CreatorThemeContextValue>({
  theme: FALLBACK_THEME,
  loading: false,
  error: false,
  refresh: () => {},
});

interface Props {
  creatorId: string;
  avatarUrl: string | null | undefined;
  bannerUrl: string | null | undefined;
  priority?: "banner" | "avatar";
  children: React.ReactNode;
}

export function CreatorThemeProvider({
  creatorId,
  avatarUrl,
  bannerUrl,
  priority = "banner",
  children,
}: Props) {
  const [theme, setTheme] = useState<ThemeTokens>(FALLBACK_THEME);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const mountedRef = useRef(true);

  const extract = useCallback(async () => {
    if (!creatorId) {
      setTheme(FALLBACK_THEME);
      return;
    }

    const cached = ThemeCache.get(creatorId);
    const valid = ThemeCache.isValid(creatorId, avatarUrl, bannerUrl);
    if (cached && valid) {
      setTheme(cached);
      return;
    }

    setLoading(true);
    setError(false);

    try {
      const images: string[] = [];
      if (priority === "banner" && bannerUrl) images.push(bannerUrl);
      if (avatarUrl) images.push(avatarUrl);
      if (priority !== "banner" && bannerUrl) images.push(bannerUrl);

      let allColors: string[] = [];
      for (const url of images) {
        if (allColors.length >= 4) break;
        const result = await extractDominantColors(url, 2, 6);
        if (!result.error && result.colors.length > 0) {
          allColors = [...allColors, ...result.colors];
        }
      }

      const unique = allColors.filter(
        (c, i) => allColors.indexOf(c) === i,
      );

      const generated = unique.length >= 2
        ? generateTheme(unique)
        : generateFallbackTheme();

      if (mountedRef.current) {
        setTheme(generated);
        ThemeCache.set(creatorId, generated, avatarUrl, bannerUrl);
      }
    } catch {
      if (mountedRef.current) {
        setTheme(FALLBACK_THEME);
        setError(true);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [creatorId, avatarUrl, bannerUrl, priority]);

  useEffect(() => {
    mountedRef.current = true;
    extract();
    return () => {
      mountedRef.current = false;
    };
  }, [extract]);

  return (
    <CreatorThemeContext.Provider
      value={{ theme, loading, error, refresh: extract }}
    >
      {children}
    </CreatorThemeContext.Provider>
  );
}
