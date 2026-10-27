"use client";

import { useEffect, useState } from "react";

/** No-flash theme script — run before paint in <head>. */
export const themeScript = `(function(){try{var t=localStorage.getItem('vkyb-theme');var d=t?t==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;document.documentElement.classList.toggle('dark',d);}catch(e){}})();`;

export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);
  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("vkyb-theme", next ? "dark" : "light");
    } catch {}
  }
  return (
    <button
      onClick={toggle}
      aria-label="Toggle theme"
      className="flex h-9 w-9 items-center justify-center rounded-full border border-border hover:bg-muted transition-colors"
    >
      <span className="text-sm">{dark ? "☾" : "☀"}</span>
    </button>
  );
}
