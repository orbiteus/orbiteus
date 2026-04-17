"""ActionResolver — RapidFuzz-based scoring for Command Palette.

Happy path: zero LLM API calls, ~1ms response time.
Optional LLM reranking when max_score < 0.4 and LLM is configured.
"""
from __future__ import annotations

import logging
from dataclasses import asdict

from rapidfuzz import fuzz, process

from orbiteus_core.ai.action import Action
from orbiteus_core.ai.registry import action_registry
from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)

# Score threshold below which LLM reranking is attempted (if configured)
LLM_RERANK_THRESHOLD = 40  # rapidfuzz returns 0-100


def _searchable_text(action: Action) -> str:
    """Concatenate all searchable strings for an action into one string."""
    parts = [action.label] + action.keywords
    if action.description:
        parts.append(action.description)
    return " | ".join(parts)


def _user_has_feature(ctx: RequestContext, feature: str) -> bool:
    """Check if the user has the required feature for an action.

    Features map to RBAC model access: 'crm.customers.view' checks
    if user has read access to 'crm.customer' model.
    """
    if not feature:
        return True
    if ctx.is_superadmin:
        return True

    # Map feature string to RBAC model access check.
    # Feature format: 'module.model_plural.operation' e.g. 'crm.customers.manage'
    # We check the RBAC cache: if cache is empty (no RBAC configured), allow all.
    from orbiteus_core.security.rbac import _model_access

    if not _model_access:
        # No RBAC rules loaded — allow all (permissive default)
        return True

    # Parse feature: 'crm.customers.view' → model='crm.customer', op='read'
    parts = feature.rsplit(".", 1)
    if len(parts) != 2:
        return True

    model_part, op_name = parts
    # Normalize: 'crm.customers' → 'crm.customer' (strip trailing 's')
    if model_part.endswith("s"):
        model_part = model_part[:-1]

    op_map = {"view": "read", "manage": "write", "create": "create", "delete": "unlink"}
    operation = op_map.get(op_name, "read")

    for role in ctx.roles:
        perms = _model_access.get(role, {}).get(model_part, {})
        if perms.get(operation, False):
            return True

    return False


def resolve(
    query: str,
    ctx: RequestContext,
    limit: int = 8,
) -> list[dict]:
    """Resolve a query to ranked Actions filtered by user RBAC.

    Returns list of dicts with "action" and "score" (0-100).
    """
    if not query or not query.strip():
        # Return all actions ordered by category
        all_actions = [
            a for a in action_registry.get_all()
            if _user_has_feature(ctx, a.requires_feature)
        ]
        return [{"action": _action_to_dict(a), "score": 100} for a in all_actions[:limit]]

    candidates = [
        a for a in action_registry.get_all()
        if _user_has_feature(ctx, a.requires_feature)
    ]
    if not candidates:
        return []

    choices = {a.id: _searchable_text(a) for a in candidates}
    action_map = {a.id: a for a in candidates}

    results = process.extract(
        query,
        choices,
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=10,  # ignore completely irrelevant matches
    )

    scored = [
        {"action": _action_to_dict(action_map[aid]), "score": round(score)}
        for _, score, aid in results
    ]

    # Optional LLM reranking (only if max score is low and LLM configured)
    if scored and scored[0]["score"] < LLM_RERANK_THRESHOLD:
        scored = _try_llm_rerank(query, scored, limit) or scored

    return scored[:limit]


def _action_to_dict(action: Action) -> dict:
    return {
        "id":               action.id,
        "label":            action.label,
        "description":      action.description,
        "category":         action.category.value,
        "target":           action.target,
        "target_url":       action.target_url,
        "icon":             action.icon,
        "module":           action.module,
        "requires_feature": action.requires_feature,
    }


def _try_llm_rerank(query: str, scored: list[dict], limit: int) -> list[dict] | None:
    """Attempt LLM-based semantic reranking when fuzzy score is low.

    Only called when ANTHROPIC_API_KEY is set in the environment.
    Returns reranked list or None to fall back to fuzzy results.
    """
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None

    try:
        import anthropic  # type: ignore[import-untyped]

        client = anthropic.Anthropic()
        action_labels = [s["action"]["label"] for s in scored]
        prompt = (
            f"User typed: '{query}'\n"
            f"Rank these ERP actions by relevance (most relevant first), "
            f"return only the action labels separated by newlines:\n"
            + "\n".join(f"- {l}" for l in action_labels)
        )
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        ranked_labels = [
            line.lstrip("- ").strip()
            for line in resp.content[0].text.strip().splitlines()
            if line.strip()
        ]
        label_order = {label: i for i, label in enumerate(ranked_labels)}
        scored.sort(key=lambda s: label_order.get(s["action"]["label"], 999))
        return scored[:limit]
    except Exception as e:
        logger.warning("LLM reranking failed, using fuzzy results: %s", e)
        return None
