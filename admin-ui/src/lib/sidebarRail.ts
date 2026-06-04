const SIDEBAR_OPEN_KEY = "orbiteus:sidebar-open";

export const NAV_WIDTH_COLLAPSED = 56;
export const NAV_WIDTH_EXPANDED = 240;

export function readSidebarOpen(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(SIDEBAR_OPEN_KEY) === "1";
  } catch {
    return false;
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

/** Sidebar shows labels only when explicitly expanded (toggle button). */
export function isSidebarExpanded(open: boolean): boolean {
  return open;
}
