"""Base module – admin-ui view configuration.

System/admin screens: Users, Companies, Partners, ir_* objects.
"""
from __future__ import annotations

UI_CONFIG = {
    "base.user": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",         "label": "Imię i nazwisko"},
                {"key": "email",        "label": "E-mail"},
                {"key": "is_active",    "label": "Aktywny"},
                {"key": "is_superadmin","label": "Superadmin"},
                {"key": "language",     "label": "Język"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",     "label": "Imię i nazwisko", "type": "text",    "required": True},
                {"key": "email",    "label": "E-mail",          "type": "email",   "required": True},
                {"key": "password", "label": "Hasło",           "type": "text"},
                {"key": "language", "label": "Język",           "type": "select",
                 "options": [{"value": "pl", "label": "Polski"}, {"value": "en", "label": "English"}]},
                {"key": "timezone", "label": "Strefa czasowa",  "type": "text"},
                {"key": "is_active","label": "Aktywny",         "type": "boolean"},
            ],
        },
    },

    "base.company": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",          "label": "Nazwa"},
                {"key": "currency_code", "label": "Waluta"},
                {"key": "country_code",  "label": "Kraj"},
                {"key": "city",          "label": "Miasto"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",          "label": "Nazwa",       "type": "text",     "required": True},
                {"key": "currency_code", "label": "Waluta",      "type": "text"},
                {"key": "country_code",  "label": "Kraj",        "type": "text"},
                {"key": "vat",           "label": "NIP",         "type": "text"},
                {"key": "email",         "label": "E-mail",      "type": "email"},
                {"key": "phone",         "label": "Telefon",     "type": "tel"},
                {"key": "street",        "label": "Ulica",       "type": "text"},
                {"key": "city",          "label": "Miasto",      "type": "text"},
                {"key": "zip_code",      "label": "Kod pocztowy","type": "text"},
            ],
        },
    },

    "base.partner": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",       "label": "Nazwa"},
                {"key": "email",      "label": "E-mail"},
                {"key": "phone",      "label": "Telefon"},
                {"key": "city",       "label": "Miasto"},
                {"key": "is_company", "label": "Firma"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",       "label": "Nazwa",       "type": "text",    "required": True},
                {"key": "email",      "label": "E-mail",      "type": "email"},
                {"key": "phone",      "label": "Telefon",     "type": "tel"},
                {"key": "mobile",     "label": "Komórkowy",   "type": "tel"},
                {"key": "street",     "label": "Ulica",       "type": "text"},
                {"key": "city",       "label": "Miasto",      "type": "text"},
                {"key": "zip_code",   "label": "Kod pocztowy","type": "text"},
                {"key": "country_code","label": "Kraj",       "type": "text"},
                {"key": "is_company", "label": "Firma",       "type": "boolean"},
                {"key": "vat",        "label": "NIP",         "type": "text"},
            ],
        },
    },

    "base.ir-config-param": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "key",         "label": "Klucz"},
                {"key": "value",       "label": "Wartość"},
                {"key": "description", "label": "Opis"},
            ],
        },
        "form": {
            "fields": [
                {"key": "key",         "label": "Klucz",  "type": "text", "required": True},
                {"key": "value",       "label": "Wartość","type": "text"},
                {"key": "description", "label": "Opis",   "type": "textarea"},
            ],
        },
    },

    "base.ir-cron": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",            "label": "Nazwa"},
                {"key": "interval_number", "label": "Co"},
                {"key": "interval_type",   "label": "Jednostka"},
                {"key": "is_active",       "label": "Aktywny"},
                {"key": "next_call",       "label": "Następne uruchomienie"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",            "label": "Nazwa",          "type": "text",    "required": True},
                {"key": "model_name",      "label": "Model",          "type": "text"},
                {"key": "function_name",   "label": "Funkcja",        "type": "text"},
                {"key": "interval_number", "label": "Co",             "type": "number"},
                {"key": "interval_type",   "label": "Jednostka",      "type": "select",
                 "options": [
                     {"value": "minutes", "label": "Minuty"},
                     {"value": "hours",   "label": "Godziny"},
                     {"value": "days",    "label": "Dni"},
                     {"value": "weeks",   "label": "Tygodnie"},
                 ]},
                {"key": "is_active",       "label": "Aktywny",        "type": "boolean"},
            ],
        },
    },
}
