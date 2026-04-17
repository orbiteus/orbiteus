"""CRM module — Action declarations for Command Palette."""
from orbiteus_core.ai import Action, ActionCategory

ACTIONS = [
    # --- Customers ---
    Action(
        id="crm.customer.list",
        label="Customers",
        keywords=[
            # EN
            "customers", "client list", "show customers", "all clients",
            # PL
            "klienci", "lista klientów", "pokaż klientów", "klient",
        ],
        description="List of all CRM customers",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/crm/customer",
        requires_feature="crm.customers.view",
        icon="users",
    ),
    Action(
        id="crm.customer.create",
        label="Create Customer",
        keywords=[
            # EN
            "new customer", "add customer", "add client", "create customer",
            # PL
            "nowy klient", "dodaj klienta", "utwórz klienta", "nowa firma",
        ],
        description="Open form to create a new customer",
        category=ActionCategory.CREATE,
        target="navigate",
        target_url="/crm/customer/new",
        requires_feature="crm.customers.manage",
        icon="user-plus",
    ),
    Action(
        id="crm.customer.prospects",
        label="Prospects & Leads",
        keywords=[
            # EN
            "prospects", "leads", "potential customers", "prospect list",
            # PL
            "prospekty", "leady", "potencjalni klienci", "prospekt",
        ],
        description="Customers with status prospect or lead",
        category=ActionCategory.SEARCH,
        target="navigate",
        target_url="/crm/customer?status=prospect",
        requires_feature="crm.customers.view",
        icon="user-search",
    ),

    # --- Opportunities ---
    Action(
        id="crm.opportunity.list",
        label="Opportunities",
        keywords=[
            # EN
            "opportunities", "deals", "sales", "deal list",
            # PL
            "szanse sprzedaży", "szanse", "deale", "sprzedaż",
        ],
        description="List of all sales opportunities",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/crm/opportunity",
        requires_feature="crm.customers.view",
        icon="briefcase",
    ),
    Action(
        id="crm.opportunity.kanban",
        label="Sales Pipeline — Kanban",
        keywords=[
            # EN
            "kanban", "pipeline", "deal board", "sales board",
            # PL
            "kanban", "pipeline", "tablica szans", "widok kanban",
        ],
        description="Kanban board view of the sales pipeline",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/crm/opportunity?view=kanban",
        requires_feature="crm.customers.view",
        icon="layout-kanban",
    ),
    Action(
        id="crm.opportunity.create",
        label="Create Opportunity",
        keywords=[
            # EN
            "new opportunity", "add deal", "new deal", "create opportunity",
            # PL
            "nowa szansa", "nowy deal", "dodaj szansę", "utwórz szansę",
        ],
        description="Open form to create a new sales opportunity",
        category=ActionCategory.CREATE,
        target="navigate",
        target_url="/crm/opportunity/new",
        requires_feature="crm.customers.manage",
        icon="plus",
    ),

    # --- Pipelines & Stages ---
    Action(
        id="crm.pipeline.list",
        label="Sales Pipelines",
        keywords=[
            # EN
            "pipeline", "sales pipeline", "pipelines", "sales funnel",
            # PL
            "pipeline", "lejek sprzedaży", "pipelines", "lejek",
        ],
        description="Manage sales pipelines and stages",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/crm/pipeline",
        requires_feature="crm.customers.view",
        icon="git-branch",
    ),
    Action(
        id="crm.stage.list",
        label="Opportunity Stages",
        keywords=[
            "stages", "opportunity stages", "won lost stage", "pipeline stages",
            "etapy", "etapy szans", "wygrana przegrana", "kolejnosc etapow",
        ],
        description="Define custom CRM stages, order and won/lost flags",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/crm/stage",
        requires_feature="crm.customers.view",
        icon="list-check",
    ),
]
