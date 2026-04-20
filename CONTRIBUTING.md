# Contributing to Orbiteus

We are glad you want to help improve the engine. This guide matches how the **Orbiteus** monorepo is organized—modules, specs, and automation—so pull requests can be reviewed and merged without surprises.

## Repository layout

| Path | Role |
|------|------|
| `backend/` | FastAPI app, `orbiteus_core`, Alembic, **modules** under `backend/modules/<name>/` |
| `admin-ui/` | Next.js 14 admin (App Router, Mantine)—dynamic renderer driven by backend `ui-config` |
| `docs/` | Cross-cutting documentation; start with **`docs/ARCHITECTURE.md`** |
| `docker-compose.yml` | Full stack (PostgreSQL, backend, admin UI) for local integration |

There is no `packages/` workspace: new backend code belongs in **`backend/`** (core vs module), new UI in **`admin-ui/`**.

## Branch model

- **`main`** — integration branch; keep it **releasable** (tests and checks you run locally should pass before you open a PR).
- **Topic branches** — one focused change per branch, using prefixes such as:
  - `feat/<short-name>` — new capability or module surface
  - `fix/<short-name>` — bug fixes
  - `chore/<short-name>` — tooling, deps, CI
  - `docs/<short-name>` — documentation only

If the project later introduces a long-lived **`develop`** branch for pre-release soak time, feature PRs may target that instead; this file and the README will be updated.

### Branch discipline

A few ground rules that keep history reviewable and fork-safe for everyone else:

- **Do not rewrite history on shared branches.** `main` and any other branch that has collaborators or open PRs against it should never receive `git push --force` or `--force-with-lease`. Rewriting published history breaks every fork, every open PR, every bookmarked commit link, and every downstream clone.
- **Force-pushing your own topic branch is fine** — as long as nobody else has checked it out and there is no PR review in progress against it.
- **Prefer `git revert` over `git reset --hard` on published branches.** If a bad commit lands on `main`, a revert keeps the record; a force-push erases it.
- **Rebase before opening a PR**, merge or rebase after. Keep PR branches current with `main` via `git fetch upstream && git rebase upstream/main`. Merging `main` into your PR branch is also acceptable if rebasing would be disruptive.
- **One concern per branch.** If you find an unrelated issue while working on a change, open a separate branch and PR for it.

## Working on features

1. **Fork** the repo and clone your fork. Add the upstream remote, for example:
   ```bash
   git remote add upstream git@github.com:orbiteus/orbiteus.git
   ```
2. **Branch from `main`** and keep it current (replace `upstream` with the remote name you use):
   ```bash
   git fetch upstream && git checkout -b feat/your-feature main
   git pull --rebase upstream main
   ```
3. **Commits** — small, scoped commits with clear messages ([Conventional Commits](https://www.conventionalcommits.org/) are welcome). Squash locally if it makes the story easier to follow.
4. **Conventions** — follow **`docs/ARCHITECTURE.md`**: module isolation (no direct imports between modules), tenant-aware repositories, RBAC, PostgreSQL-only assumptions.

## Spec-driven development

Orbiteus is **spec-first** per architecture rules—not a separate `.ai/specs/` tree.

1. **Read** `docs/ARCHITECTURE.md` (phases, layers, non‑negotiable principles) before large changes.
2. **Per module** — each module has **`backend/modules/<module>/docs/spec.md`**. For new modules or behavior that changes contracts, **create or update that spec** before or alongside code so design stays explicit.
3. **Core changes** — significant `orbiteus_core` behavior should be reflected in `backend/orbiteus_core/docs/spec.md` when it exists, or in `docs/ARCHITECTURE.md` if it is a cross-cutting decision.
4. **Changelog** — for user-visible or noteworthy changes, add a line under **`[Unreleased]`** in `CHANGELOG.md` ([Keep a Changelog](https://keepachangelog.com/)).

## Frontend copy and i18n

User-visible strings in the admin UI live in **`admin-ui/src/lib/i18n.ts`** (`en` and `pl`). If you add or change copy, **update both locales** so the UI stays consistent.

## Tests and local checks

| Area | Typical commands |
|------|------------------|
| Backend | From `backend/`: `uv run pytest` (or your configured Python env with dev deps) |
| Admin UI | From `admin-ui/`: `npm install` then `npm test` |
| Full stack | From repo root: `docker compose up --build` — use for integration / manual verification |

Run the checks relevant to your change before requesting review.

## Pull requests

- **Target `main`** unless maintainers ask for a different base (e.g. a future `develop`).
- **Describe** user impact, any architectural tradeoffs, and **what you tested** (unit tests, manual paths, Docker if applicable).
- **UI changes** — screenshots or a short screen recording help reviewers.
- **API changes** — note OpenAPI / client impact; migrations belong in Alembic under `backend/migrations/`.
- **Link** related GitHub issues or discussions when applicable.
- **CI** — ensure the branch is up to date with `main` and checks are green before requesting review.
- If you need early **design or architecture** alignment, open a draft PR or issue and @mention maintainers.

## Helpful resources

- **Architecture (living spec):** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Module examples:** `backend/modules/base/`, `backend/modules/crm/` (each with `docs/spec.md`, `manifest.py`, security, views)
- **Issues and discussions:** [GitHub Issues](https://github.com/orbiteus/orbiteus/issues)

Thanks for helping make Orbiteus a solid, composable foundation for ERP/CRM-style products.
