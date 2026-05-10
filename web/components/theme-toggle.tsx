"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    // Render a placeholder so layout doesn't shift; theme is unknown until hydration.
    return <div className="h-8 w-8" aria-hidden />;
  }

  const isDark = resolvedTheme === "dark";
  return (
    <button
      type="button"
      aria-label={isDark ? "라이트 모드" : "다크 모드"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="grid h-8 w-8 place-items-center rounded-md text-slate-600 transition hover:bg-slate-100 hover:text-indigo-600 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-indigo-400"
    >
      {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}
