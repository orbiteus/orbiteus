# ADR-0024: UI i18n as module catalogs (English canonical)

- **Status:** Accepted
- **Date:** 2026-05-29
- **Context tags:** i18n, modules, admin-ui, portal-ui
- **Supersedes:** monolithic `packages/i18n` message bundles as source of truth

## Context

UI strings lived in `packages/i18n/src/messages.ts` (frontend bundle) while module
`i18n/*.json` loading existed only on the backend. Two sources of truth caused
drift and blocked the “extend i18n by adding modules” model.

## Decision

1. **Canonical English** lives under `modules/base/i18n/en.json` (fail-fast at
   bootstrap if empty). No other locales in `base`.
2. **Additional locales** ship in optional modules (reference: `modules/locales`
   for `pl`, `de`, `fr`). Each module declares `i18n` / `i18n_locales` in
   `manifest.py` and is registered in `backend/api.py`.
3. **Merge order:** `en` base → locale file → later modules in load order →
   `base.ui-translation` (DB).
4. **SPA** loads merged catalogs only via:
   - `GET /api/base/i18n/locales`
   - `GET /api/base/i18n/messages/{lang}`
5. **`@orbiteus/i18n`** keeps `useT`, `I18nProvider`, merge helpers — no full
   catalogs in TypeScript (public routes use static fallbacks until authenticated).

## Consequences

- New UI keys: add to `en.json`, mirror in each installed locale module;
  run `scripts/check_i18n.py` in CI.
- `registerLanguagePack()` is deprecated (white-label frontend overlay only).
- Export script `scripts/export_i18n_to_base.py` retained for one-off migrations.

## References

- `docs/19-i18n.md`
- `backend/modules/base/i18n/README.md`
