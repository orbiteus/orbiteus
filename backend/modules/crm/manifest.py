"""CRM module manifest."""

MANIFEST = {
    "name": "CRM",
    "version": "1.0.0",
    "depends_on": ["base", "auth"],
    "models": [
        "crm.customer",
        "crm.pipeline",
        "crm.stage",
        "crm.opportunity",
    ],
    "category": "Sales",
    "auto_install": False,
    "data": [
        "security/access.yaml",
        "view/customer_views.xml",
        "view/opportunity_views.xml",
        "view/stage_views.xml",
    ],
    "menus": [
        {"name": "CRM", "sequence": 10, "icon": "users"},
        {"name": "Customers",    "parent": "CRM", "sequence": 10, "model": "crm.customer"},
        {"name": "Opportunities","parent": "CRM", "sequence": 20, "model": "crm.opportunity"},
        {"name": "Pipelines",    "parent": "CRM", "sequence": 30, "model": "crm.pipeline"},
        {"name": "Stages",       "parent": "CRM", "sequence": 40, "model": "crm.stage"},
    ],
    # view config module path – loaded by engine to expose GET /api/base/ui-config
    "view_config": "modules.crm.view.config",
}
