# ADR-0019: Agent delegation and scheduled runs

- **Status:** Accepted
- **Date:** 2026-05-28
- **Context tags:** backend, ai, agents
- **Supersedes:** partial scope of ADR-0018 deferred items

## Context

ADR-0018 shipped single-agent runs with a multi-turn tool loop. Product owners
and developers need:

1. **Delegation** — one agent spawns a child run on another agent (swarm-lite).
2. **Scheduling** — recurring agent runs without manual triggers.
3. **Streaming tool loops** — `/api/ai/chat?stream=1` must execute tools across
   turns, not only on the first provider response.
4. **Realtime run status** — admin UI polls/subscribes while async runs execute.

Full LangGraph/Temporal orchestration remains out of scope (ADR-0015).

## Decision

1. **Delegation**
   - Add `parent_run_id`, `depth` on `base.agent-run`.
   - Add `can_delegate`, `allowed_delegate_slugs` on `base.agent`.
   - Expose `delegate_agent` tool when `can_delegate=true`.
   - `MAX_DELEGATION_DEPTH = 3` enforced in `orbiteus_core/ai/delegation.py`.

2. **Scheduling**
   - Add `schedule_interval_minutes`, `schedule_prompt`, `schedule_last_run_at`
     on `base.agent`.
   - Celery Beat task `tasks.ai_tasks.poll_scheduled_agents` every 5 minutes.

3. **Streaming**
   - `run_agent_loop_stream()` yields `text`, `tool_call`, `tool_result`, `done`.
   - `/api/ai/chat?stream=1` uses the streaming loop.

4. **Realtime**
   - `publish_agent_run_update()` publishes to standard SSE topics for
     `base.agent-run` on status transitions.

5. **Showcase**
   - Seed `crm-analyst` (read-only) and enable `crm-assistant` to delegate to it.

## Consequences

- Child runs inherit the parent's `RequestContext` (RBAC upper bound unchanged).
- Delegation cycles (A→B→A) are blocked by depth cap and self-delegation check.
- Scheduled runs use `actor=system` with superadmin context per tenant — explicit
  RBAC scope, never elevated beyond tenant.
- Portal-scoped agent runs remain tied to ADR-0007 portal auth; internal/admin
  scope is fully supported today.

## Alternatives considered

- Temporal workflows for delegation — rejected (ADR-0015).
- Separate `base.agent-schedule` table — rejected; fields on `base.agent` suffice.

## References

- `docs/37-ai-agents.md`
- ADR-0018, ADR-0013, ADR-0015
