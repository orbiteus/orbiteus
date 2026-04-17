"""Base module manifest."""

MANIFEST = {
    "name": "Base",
    "version": "1.0.0",
    "depends_on": [],  # No dependencies – loaded first
    "models": [
        "base.tenant",
        "base.company",
        "base.partner",
        "base.user",
        "base.ir-model",
        "base.ir-model-field",
        "base.ir-model-access",
        "base.ir-rule",
        "base.ir-ui-menu",
        "base.ir-sequence",
        "base.ir-config-param",
        "base.ir-cron",
        "base.ir-ui-view",
    ],
    "category": "Core",
    "auto_install": True,
    "data": [
        "security/access.yaml",
    ],
    "menus": [
        {"name": "Technical", "sequence": 9999, "groups": ["base.group_system"]},
    ],
}
