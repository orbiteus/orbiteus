"use client";

/** Full-page navigation — used on public routes where App Router client transitions can stall. */
export function hardNavigate(href: string): void {
  if (typeof window === "undefined") return;
  window.location.assign(href);
}
