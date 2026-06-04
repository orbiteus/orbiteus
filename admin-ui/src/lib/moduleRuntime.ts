/**
 * Client-side refresh after module catalog on/off.
 *
 * Backend: soft toggle (ui-config, i18n, …) — routes stay mounted until process
 * restart. SPA: bust TanStack Query caches; redirect off disabled module routes.
 */
import { invalidateUiConfigCache } from "./modelConfig";
import { getQueryClient } from "./queryClient";

export type ModuleToggleDetail = {
  module: string;
  enabled: boolean;
};

export const MODULES_CHANGED_EVENT = "orbiteus:modules-changed";

/** Bust server-state that depends on `module.<name>.enabled`. */
export function invalidateModuleRuntimeCaches(): void {
  invalidateUiConfigCache();
  const qc = getQueryClient();
  void qc.invalidateQueries({ queryKey: ["i18n"] });
  void qc.invalidateQueries({ queryKey: ["resource"] });
  void qc.invalidateQueries({ queryKey: ["attachments"] });
}

export function dispatchModulesChanged(detail: ModuleToggleDetail): void {
  window.dispatchEvent(
    new CustomEvent(MODULES_CHANGED_EVENT, { detail }),
  );
}

/** Redirect when the current screen belongs to a module that was just disabled. */
export function redirectIfOnDisabledModuleRoute(moduleName: string, enabled: boolean): void {
  if (enabled || typeof window === "undefined") return;
  const path = window.location.pathname;
  const prefix = `/${moduleName}`;
  if (path === prefix || path.startsWith(`${prefix}/`)) {
    window.location.assign("/");
  }
}

/** Call after PATCH /api/base/modules/{name} succeeds. */
export function applyModuleToggleSideEffects(moduleName: string, enabled: boolean): void {
  invalidateModuleRuntimeCaches();
  dispatchModulesChanged({ module: moduleName, enabled });
  redirectIfOnDisabledModuleRoute(moduleName, enabled);
}
