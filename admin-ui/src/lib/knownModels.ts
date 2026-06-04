import type { UiConfig } from "@/lib/api";
import { findModel } from "@/lib/modelConfig";

const STATIC_PREFIXES = [
  "/welcome",
  "/modules",
  "/connectivity/",
  "/technical/",
  "/users/",
  "/reset/",
  "/forgot-password",
  "/login",
];

/** Removed product modules — no longer in the engine (see backend registry). */
const REMOVED_MODULES = new Set(["crm"]);

function installedModuleNames(uiConfig: UiConfig | undefined): Set<string> {
  return new Set((uiConfig?.modules ?? []).map((m) => m.name));
}

/** All models present in ui-config (including ui_hidden engine models). */
export function knownModelNames(uiConfig: UiConfig | undefined): Set<string> {
  const names = new Set<string>();
  for (const mod of uiConfig?.modules ?? []) {
    for (const model of mod.models) {
      names.add(model.name);
    }
  }
  return names;
}

export function isKnownModel(
  uiConfig: UiConfig | undefined,
  module: string,
  modelSegment: string,
): boolean {
  if (!installedModuleNames(uiConfig).has(module) || REMOVED_MODULES.has(module)) {
    return false;
  }
  if (!uiConfig) {
    return false;
  }
  return findModel(uiConfig, module, modelSegment) !== null;
}

/** Block palette links and routes for removed product modules (e.g. legacy CRM). */
export function isAllowedAppPath(
  path: string,
  uiConfig: UiConfig | undefined,
): boolean {
  if (!path || path === "/") return true;
  if (STATIC_PREFIXES.some((p) => path === p || path.startsWith(p))) return true;

  const parts = path.split("/").filter(Boolean);
  if (parts.length < 2) return true;

  const [mod, modelPart] = parts;
  return isKnownModel(uiConfig, mod, modelPart);
}
