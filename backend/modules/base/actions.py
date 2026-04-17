"""Base module — Action declarations for Command Palette."""
from orbiteus_core.ai import Action, ActionCategory

ACTIONS = [
    Action(
        id="base.company.list",
        label="Companies",
        keywords=[
            # EN
            "companies", "company list", "organizations", "firms",
            # PL
            "firmy", "spółki", "firma", "lista firm",
        ],
        description="List of companies and organizations",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/base/company",
        icon="building",
    ),
    Action(
        id="base.user.list",
        label="Users",
        keywords=[
            # EN
            "users", "user list", "accounts", "team members",
            # PL
            "użytkownicy", "pracownicy", "konta", "lista użytkowników",
        ],
        description="Manage system users",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/base/user",
        icon="users",
    ),
    Action(
        id="base.partner.list",
        label="Partners",
        keywords=[
            # EN
            "partners", "vendors", "suppliers", "contacts", "partner list",
            # PL
            "kontrahenci", "dostawcy", "partnerzy", "lista kontrahentów",
        ],
        description="List of partners and contacts",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/base/partner",
        icon="address-book",
    ),
    Action(
        id="technical.params",
        label="System Parameters",
        keywords=[
            # EN
            "parameters", "config", "system config", "settings", "system params",
            # PL
            "parametry", "ustawienia systemu", "konfiguracja", "parametry systemu",
        ],
        description="Global system configuration parameters (IrConfigParam)",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/technical/params",
        icon="adjustments",
    ),
    Action(
        id="technical.access",
        label="Access Rights",
        keywords=[
            # EN
            "access", "rbac", "permissions", "roles", "security", "access rights",
            # PL
            "uprawnienia", "role", "prawa dostępu", "bezpieczeństwo",
        ],
        description="Manage model access rights (ir_model_access)",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/technical/access",
        icon="shield-lock",
    ),
    Action(
        id="technical.sequences",
        label="Sequences",
        keywords=[
            # EN
            "sequences", "numbering", "document numbers", "sequence list",
            # PL
            "sekwencje", "numeracja", "numery dokumentów", "numerowanie",
        ],
        description="Manage document numbering sequences",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/technical/sequences",
        icon="list-numbers",
    ),
    Action(
        id="technical.crons",
        label="Cron Jobs",
        keywords=[
            # EN
            "cron", "cron jobs", "scheduled jobs", "scheduler", "automation",
            # PL
            "cron", "zadania cron", "zaplanowane zadania", "automatyzacja",
        ],
        description="Scheduled automated tasks",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/technical/crons",
        icon="clock-play",
    ),
]
