/** Route → message key for sidebar / breadcrumbs (catalog lives in modules/base/i18n). */

import { SHELL_FALLBACK_EN } from "./shell-fallbacks";

export const NAV_LABEL_KEYS: Record<string, string> = {
  "/": "nav.dashboard",
  "/technical/ai-integration": "nav.ai.integration",
  "/technical/agent-console": "nav.ai.agentConsole",
  "/base/agent": "nav.ai.agents",
  "/base/agent-run": "nav.ai.agentRuns",
  "/base/user": "nav.settings.users",
  "/base/role": "nav.settings.roles",
  "/base/model-access": "nav.settings.access",
  "/connectivity/mail": "nav.settings.mail",
  "/connectivity/webhooks": "nav.settings.webhooks",
  "/modules": "nav.settings.modules",
  "/technical/system-status": "nav.technical.status",
  "/technical/attachments": "nav.technical.attachments",
  "/base/registry-model": "nav.technical.models",
  "/base/record-rule": "nav.technical.rules",
  "/base/config-param": "nav.technical.parameters",
  "/technical/audit-log": "nav.technical.audit",
  "/technical/languages": "nav.technical.languages",
};

export function translateMessageKey(t: (key: string) => string, key: string): string {
  const msg = t(key);
  if (msg !== key) return msg;
  return SHELL_FALLBACK_EN[key] ?? key;
}

export function translateNavLabel(t: (key: string) => string, href: string, fallback: string): string {
  const key = NAV_LABEL_KEYS[href];
  if (!key) return fallback;
  return translateMessageKey(t, key);
}
