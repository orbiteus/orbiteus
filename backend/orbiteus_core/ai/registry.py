"""ActionRegistry — singleton that holds all registered Actions.

Usage:
    # In module lifecycle (registry.py):
    action_registry.register_module("crm", ACTIONS)

    # In API endpoint:
    all_actions = action_registry.get_all()
"""
from __future__ import annotations

import logging
from typing import Sequence

from orbiteus_core.ai.action import Action

logger = logging.getLogger(__name__)


class ActionRegistry:
    """Thread-safe (GIL) singleton registry for all module Actions."""

    def __init__(self) -> None:
        self._actions: dict[str, Action] = {}  # id → Action

    def register_module(self, module_name: str, actions: Sequence[Action]) -> None:
        """Register all Actions from a module. Called during module bootstrap."""
        for action in actions:
            action.module = module_name
            if action.id in self._actions:
                logger.warning(
                    "Action '%s' already registered (from '%s'), overwriting with '%s'",
                    action.id, self._actions[action.id].module, module_name,
                )
            self._actions[action.id] = action
        logger.info(
            "Module '%s' registered %d actions", module_name, len(actions),
        )

    def get_all(self) -> list[Action]:
        return list(self._actions.values())

    def get(self, action_id: str) -> Action | None:
        return self._actions.get(action_id)

    def clear(self) -> None:
        """Reset registry (used in tests)."""
        self._actions.clear()


# Singleton — import and use everywhere
action_registry = ActionRegistry()
