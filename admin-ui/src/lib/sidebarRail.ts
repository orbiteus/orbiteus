const SIDEBAR_OPEN_KEY = "orbiteus:sidebar-open";

export { SIDEBAR_OPEN_KEY };

export const NAV_WIDTH_COLLAPSED = 56;
export const NAV_WIDTH_EXPANDED = 240;

export function readSidebarOpen(): boolean {
  if (typeof window === "undefined") return true;
  try {
    const raw = window.localStorage.getItem(SIDEBAR_OPEN_KEY);
    if (raw === null) return true;
    return raw === "1";
  } catch {
    return true;
  }
}

export function writeSidebarOpen(open: boolean): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(SIDEBAR_OPEN_KEY, open ? "1" : "0");
  } catch {
    /* ignore */
  }
}

/** Sidebar shows labels when expanded (240px rail). */
export function isSidebarExpanded(open: boolean): boolean {
  return open;
}
