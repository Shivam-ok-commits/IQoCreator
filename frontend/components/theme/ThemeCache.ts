import { ThemeTokens } from "./ThemeTokens";

interface CacheEntry {
  theme: ThemeTokens;
  avatarHash: string | null;
  bannerHash: string | null;
  timestamp: number;
}

const STORAGE_KEY_PREFIX = "iqc_theme_";
const TTL_MS = 24 * 60 * 60 * 1000;

function hashUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  let hash = 0;
  for (let i = 0; i < url.length; i++) {
    const char = url.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0;
  }
  return hash.toString(36);
}

function buildKey(creatorId: string): string {
  return `${STORAGE_KEY_PREFIX}${creatorId}`;
}

export const ThemeCache = {
  get(creatorId: string): ThemeTokens | null {
    try {
      const raw = localStorage.getItem(buildKey(creatorId));
      if (!raw) return null;
      const entry: CacheEntry = JSON.parse(raw);
      if (Date.now() - entry.timestamp > TTL_MS) {
        localStorage.removeItem(buildKey(creatorId));
        return null;
      }
      return entry.theme;
    } catch {
      return null;
    }
  },

  set(
    creatorId: string,
    theme: ThemeTokens,
    avatarUrl: string | null | undefined,
    bannerUrl: string | null | undefined,
  ): void {
    try {
      const entry: CacheEntry = {
        theme,
        avatarHash: hashUrl(avatarUrl),
        bannerHash: hashUrl(bannerUrl),
        timestamp: Date.now(),
      };
      localStorage.setItem(buildKey(creatorId), JSON.stringify(entry));
    } catch {
      /* storage full or disabled — silently degrade */
    }
  },

  isValid(
    creatorId: string,
    avatarUrl: string | null | undefined,
    bannerUrl: string | null | undefined,
  ): boolean {
    try {
      const raw = localStorage.getItem(buildKey(creatorId));
      if (!raw) return false;
      const entry: CacheEntry = JSON.parse(raw);
      const sameAvatar = hashUrl(avatarUrl) === entry.avatarHash;
      const sameBanner = hashUrl(bannerUrl) === entry.bannerHash;
      return sameAvatar && sameBanner;
    } catch {
      return false;
    }
  },

  invalidate(creatorId: string): void {
    try {
      localStorage.removeItem(buildKey(creatorId));
    } catch {
      /* noop */
    }
  },
};
