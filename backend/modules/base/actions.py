"""Base module — Action declarations for Command Palette."""
from orbiteus_core.ai import Action, ActionCategory

ACTIONS = [
    Action(
        id="base.company.list",
        label="Companies",
        keywords=["companies", "company list", "organizations", "firms"],
        description="List of companies and organizations",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/base/company",
        icon="building",
    ),
    Action(
        id="base.user.list",
        label="Users",
        keywords=["users", "user list", "accounts", "team members"],
        description="Manage system users",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/base/user",
        icon="users",
    ),
    Action(
        id="technical.params",
        label="System Parameters",
        keywords=["parameters", "config", "system config", "settings", "system params"],
        description="Global system configuration parameters (ConfigParam)",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/technical/params",
        icon="adjustments",
    ),
    Action(
        id="technical.access",
        label="Access Rights",
        keywords=["access", "rbac", "permissions", "roles", "security", "access rights"],
        description="Manage model access rights (base_model_access)",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/technical/access",
        icon="shield-lock",
    ),
]
