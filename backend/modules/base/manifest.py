"""Base module manifest."""

MANIFEST = {
    "name": "Base",
    "version": "1.0.0",
    "depends_on": [],  # No dependencies – loaded first
    "models": [
        "base.company",
        "base.user",
        "base.role",
        "base.registry-model",
        "base.model-access",
        "base.record-rule",
        "base.config-param",
        "base.ui-translation",
        "base.agent",
        "base.agent-run",
    ],
    "category": "Core",
    "auto_install": True,
    "i18n": ["en"],
    "i18n_locales": [
        {"code": "en", "label": "English", "dayjs": "en"},
    ],
    "ui_hidden_models": [
        "base.registry-model-field",
        "base.registry-model",
        "base.model-access",
        "base.record-rule",
        "base.config-param",
        "base.ui-translation",
        "base.agent-run",
    ],
    "data": [
        "security/access.yaml",
        "views/base.user.list.view.json",
        "views/base.user.form.view.json",
        "views/base.registry-model.list.view.json",
        "views/base.registry-model.form.view.json",
        "views/base.record-rule.list.view.json",
        "views/base.record-rule.form.view.json",
        "views/base.config-param.list.view.json",
        "views/base.config-param.form.view.json",
        "views/base.model-access.list.view.json",
        "views/base.model-access.form.view.json",
    ],
    "menus": [
        {"name": "Technical", "sequence": 9999, "groups": ["base.group_system"]},
    ],
}
