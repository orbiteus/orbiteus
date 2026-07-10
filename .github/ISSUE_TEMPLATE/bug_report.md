---
name: Bug report
about: Something is not behaving the way the docs, specs, or architecture say it should.
title: "bug: <short description>"
labels: ["bug"]
assignees: []
---

<!--
Please search existing issues first to avoid duplicates.

Do NOT open a public issue for security findings. Use GitHub's private
vulnerability reporting instead (see SECURITY.md).
-->

## Summary

<!-- One-line description of the problem. -->

## Environment

- Orbiteus version / commit: <!-- e.g. v0.1.0 or commit sha -->
- Install method: <!-- docker compose | native (Python 3.12 + Node 20) -->
- OS: <!-- e.g. macOS 14.5, Ubuntu 22.04 -->
- Browser (if admin UI): <!-- e.g. Chrome 131 -->

## Steps to reproduce

1. ...
2. ...
3. ...

## Expected behaviour

<!-- What should have happened? Reference `docs/ARCHITECTURE.md` or a module `docs/spec.md` if relevant. -->

## Actual behaviour

<!-- What happened instead? Include error messages, stack traces, or screenshots. -->

## Impact

- [ ] Blocks core workflow (data loss, auth, tenant isolation, RBAC)
- [ ] Regression from previous release
- [ ] Cosmetic / polish

## Additional context

<!-- Logs, relevant modules (`backend/modules/<name>/`), related issues, anything else useful. -->
