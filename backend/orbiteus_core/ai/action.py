"""Action dataclass — the unit of business logic for the Command Palette."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ActionCategory(str, Enum):
    NAVIGATE = "navigate"   # open a view / page
    CREATE   = "create"     # open a creation form
    REPORT   = "report"     # open a report / analytics view
    EXECUTE  = "execute"    # call API directly, no form (e.g. send email)
    SEARCH   = "search"     # open a view with a pre-set filter


@dataclass
class Action:
    """Declarative description of a single business action.

    Registered by each module's actions.py via ActionRegistry.
    Resolved by ActionResolver (RapidFuzz, no LLM in happy path).
    Executed by the frontend: router.push(target_url) or API call.
    """
    id: str                          # unique: "crm.customer.create"
    label: str                       # displayed in Command Palette
    keywords: list[str] = field(default_factory=list)   # extra search terms
    description: str = ""
    category: ActionCategory = ActionCategory.NAVIGATE
    target: str = "navigate"         # "navigate" | "modal" | "execute"
    target_url: str = ""             # path for navigate / modal
    requires_feature: str = ""       # RBAC feature flag (empty = always visible)
    icon: str = ""                   # tabler icon name e.g. "user-plus"
    module: str = ""                 # set automatically by ActionRegistry
