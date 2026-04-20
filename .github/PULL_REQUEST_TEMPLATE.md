<!--
Thanks for contributing to Orbiteus. Please fill in the sections below.
Keep PRs focused and small where possible.
-->

## Summary

<!-- What does this PR change, and why? One or two sentences. -->

## Type of change

- [ ] `feat` — new capability or module surface
- [ ] `fix` — bug fix
- [ ] `chore` — tooling, deps, CI
- [ ] `docs` — documentation only
- [ ] `refactor` — no behaviour change
- [ ] `test` — adds or updates tests
- [ ] Other: ___

## Spec / issue reference

<!--
Per CONTRIBUTING.md, Orbiteus is spec-first:

- Module changes should reference or update `backend/modules/<module>/docs/spec.md`.
- Core changes should reference `docs/ARCHITECTURE.md` or a `docs/` spec.
- Link the related GitHub issue or RFC when one exists.
-->

- Spec: ___
- Issue / RFC: #___

## What I tested

<!--
Be specific. The reviewer should be able to reproduce.

Backend:  cd backend && pytest -q
Admin UI: cd admin-ui && npm test
Full:     docker compose up --build
-->

- [ ] Backend unit tests (`pytest`)
- [ ] Admin UI unit tests (`npm test`)
- [ ] Manual verification (docker compose)
- [ ] Not applicable (docs / CI only)

## Screenshots / screen recordings

<!-- Required for UI changes. Delete this section if not applicable. -->

## Checklist

- [ ] Branch name follows the `feat|fix|chore|docs/<short-name>` convention
- [ ] `CHANGELOG.md` updated under `[Unreleased]` if this is user-visible
- [ ] i18n updated in both `en` and `pl` in `admin-ui/src/lib/i18n.ts` if copy changed
- [ ] No new module-to-module imports (modules only talk via `orbiteus_core`)
- [ ] Tenant isolation respected (no direct `tenant_id` writes in module code)
- [ ] CI is green
