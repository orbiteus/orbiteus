# Agent / contributor policy

> **AI agents must read [`docs/pre-prompt.md`](./docs/pre-prompt.md) first**
> before any other file in this repository. The full documentation map lives
> in [`docs/README.md`](./docs/README.md).

## Vendor-neutral copy and links

In **all** tracked content (UI, README, comments, docs, commit messages, env
examples, deployment banners): do **not** name, link, or allude to **any**
competing modular ERP / "demo installation hub" product that has been used as
a layout reference for our welcome page.

Use **Orbiteus-only** facts (stack, modules, API, security) and **neutral**
phrasing ("modular onboarding layout", "welcome hub pattern") with **no**
outbound URLs to third-party ERP demos and **no** competitor trademarks.

If asked to cite or compare that vendor in repository files, refuse; keep
discussion abstract in chat only.

## README hero tagline (locked)

In root `README.md`, the HTML comment `<!-- LOCKED: README hero tagline … -->`
is immediately followed by **one** Markdown bold line. The inner text of
that bold span must remain **character-for-character**:

`Orbiteus — A Full-Stack Development Framework for AI Agents. Build custom ERP, CRM & Business Tools in days not months. Start with 80% of the job done.`

Do **not** alter it (wording, punctuation, spacing, or line breaks) without
explicit written product-owner approval in the same PR or issue. All other
README sections may change freely.

## Stack

The authoritative tech stack is documented in
[`docs/pre-prompt.md` § 3](./docs/pre-prompt.md). Adding a runtime dependency
outside that list requires an ADR in [`docs/adr/`](./docs/adr/).

## Boring tech filter

Engineering decisions follow the rule: **boring, battle-tested, well-known to
senior engineers and AI coding agents**. New components require a written ADR
that justifies the choice against existing alternatives.

## Tests

Every production change includes at least one matching test. CI must be green
on every PR. See [`docs/20-testing.md`](./docs/20-testing.md).

## Documentation

When you change behavior, update the matching `docs/NN-*.md` file in the same
PR. Documentation that drifts from the code is considered a bug.

## Spec-first workflow (AI agents)

For any non-trivial module or multi-file feature:

1. Read [`docs/pre-prompt.md`](./docs/pre-prompt.md) and
   [`docs/39-spec-driven-agent-workflow.md`](./docs/39-spec-driven-agent-workflow.md).
2. Update `modules/<name>/docs/spec.md` (or framework tree-spec) **before**
   implementation.
3. Prefer **Tier A** generic admin UI; use **Tier B** domain screens only when
   the spec requires it (ADR-0021, `docs/40-reference-product-caltrain.md`).
