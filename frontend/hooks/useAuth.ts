"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type MeResponse } from "@/services/api";

export function useAuth() {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkSession = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.me();
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkSession();
  }, [checkSession]);

  const logout = useCallback(async () => {
    try {
      await api.logout();
      setUser(null);
    } catch {
      setUser(null);
    }
  }, []);

  const login = useCallback(() => {
    api.login();
  }, []);

  return {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    logout,
    checkSession,
  };
}
