"use client";

import { useContext } from "react";
import { CreatorThemeContext } from "@/components/theme/CreatorThemeProvider";

export function useCreatorTheme() {
  return useContext(CreatorThemeContext);
}
