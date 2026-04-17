"""Orbiteus AI-native layer.

Exports the public surface used by module actions.py files:
    from orbiteus_core.ai import Action, ActionCategory

The CommandPalette (Cmd+K) resolves user queries through ActionResolver
using RapidFuzz — zero LLM API calls in the happy path.
"""
from orbiteus_core.ai.action import Action, ActionCategory
from orbiteus_core.ai.registry import action_registry

__all__ = ["Action", "ActionCategory", "action_registry"]
