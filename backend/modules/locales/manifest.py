"""Reference locale pack — ship extra UI languages as modules, not in base."""

MANIFEST = {
    "name": "locales",
    "version": "1.0.0",
    "depends_on": ["base"],
    "models": [],
    "category": "Localization",
    "auto_install": True,
    "i18n": ["pl", "de", "fr"],
    "i18n_locales": [
        {"code": "pl", "label": "Polski", "dayjs": "pl"},
        {"code": "de", "label": "Deutsch", "dayjs": "de"},
        {"code": "fr", "label": "Français", "dayjs": "fr"},
    ],
}
