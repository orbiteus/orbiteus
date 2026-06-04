import type { MessageCatalog } from "./core";

/**
 * English labels for shell navigation and the Languages technical page.
 * Fills gaps when the API catalog is stale (e.g. backend not restarted after deploy).
 * Canonical copy lives in backend/modules/base/i18n/en.json — keep in sync when changing nav.
 */
export const SHELL_FALLBACK_EN: MessageCatalog = {
  "nav.dashboard": "Dashboard",
  "nav.group.apps": "Apps",
  "nav.group.system": "System",
  "nav.section.ai": "AI",
  "nav.section.settings": "Settings",
  "nav.section.technical": "Technical",
  "nav.ai.integration": "AI Integration",
  "nav.ai.agentConsole": "Agent Console",
  "nav.ai.agents": "Agents",
  "nav.ai.agentRuns": "Agent runs",
  "nav.settings.users": "Users",
  "nav.settings.roles": "Roles",
  "nav.settings.access": "Access rights",
  "nav.settings.mail": "Mail",
  "nav.settings.webhooks": "Webhooks",
  "nav.settings.modules": "Module catalog",
  "nav.technical.status": "System status",
  "nav.technical.attachments": "Attachments",
  "nav.technical.models": "Models",
  "nav.technical.rules": "Rules",
  "nav.technical.parameters": "Parameters",
  "nav.technical.audit": "Audit log",
  "nav.technical.languages": "Languages",
  "nav.collapse": "Collapse",
  "nav.expand": "Expand menu",
  "nav.collapseMenu": "Collapse menu",
  "nav.searchActions": "Search actions",
  "languages.page.title": "UI languages",
  "languages.page.subtitle":
    "Message catalogs are loaded from engine modules at startup. English in the base module is the canonical fallback.",
  "languages.core.title": "Core pack (base module)",
  "languages.core.canonical": "Canonical locale",
  "languages.core.path": "Catalog path",
  "languages.core.keyCount": "Message keys",
  "languages.core.description":
    "English is the only locale in the base module. Define every UI key in en.json first. Other languages must ship as separate modules. Missing keys inherit English at runtime.",
  "languages.registered.title": "Registered locales",
  "languages.registered.empty": "No locales registered.",
  "languages.table.code": "Code",
  "languages.table.label": "Label",
  "languages.table.dayjs": "Date locale",
  "languages.table.source": "Source",
  "languages.table.module": "Module",
  "languages.badge.core": "Core",
  "languages.badge.extension": "Module",
  "languages.modulePack.title": "Adding a new language pack",
  "languages.modulePack.intro":
    "Register additional UI translations by shipping a module — not by editing the admin UI bundle.",
  "languages.modulePack.step1":
    "Create or extend a module under backend/modules/<name>/ with an i18n/ directory.",
  "languages.modulePack.step2": "Add JSON catalogs (e.g. i18n/es.json) and declare them in manifest.py.",
  "languages.modulePack.step3":
    "Restart the backend so the module registry loads catalogs. Locales appear here and in the user language picker.",
  "languages.modulePack.overrides":
    "Optional per-key overrides without redeploy: base.ui-translation (highest priority). Product copy still belongs in module i18n JSON files.",
  "languages.modulePack.linkDocs": "See backend/modules/base/i18n/README.md in the repository.",
};
