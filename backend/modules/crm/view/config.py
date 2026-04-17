"""CRM module – admin-ui view configuration.

Declares what views are available per model and how to render them.
The engine reads this config to auto-generate or guide the admin-ui.
"""
from __future__ import annotations

UI_CONFIG = {
    "crm.customer": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",    "label": "Nazwa"},
                {"key": "email",   "label": "E-mail"},
                {"key": "phone",   "label": "Telefon"},
                {"key": "status",  "label": "Status"},
                {"key": "city",    "label": "Miasto"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",        "label": "Nazwa",       "type": "text",    "required": True},
                {"key": "email",       "label": "E-mail",      "type": "email"},
                {"key": "phone",       "label": "Telefon",     "type": "tel"},
                {"key": "mobile",      "label": "Komórkowy",   "type": "tel"},
                {"key": "website",     "label": "Strona WWW",  "type": "text"},
                {"key": "street",      "label": "Ulica",       "type": "text"},
                {"key": "city",        "label": "Miasto",      "type": "text"},
                {"key": "country_code","label": "Kraj",        "type": "text"},
                {"key": "is_company",  "label": "Firma",       "type": "boolean"},
                {"key": "vat",         "label": "NIP",         "type": "text"},
                {"key": "status",      "label": "Status",      "type": "select",
                 "options": [
                     {"value": "lead",     "label": "Lead"},
                     {"value": "prospect", "label": "Prospect"},
                     {"value": "customer", "label": "Klient"},
                     {"value": "churned",  "label": "Churned"},
                 ]},
                {"key": "notes",       "label": "Notatki",     "type": "textarea"},
            ],
        },
    },

    "crm.opportunity": {
        "views": ["list", "kanban", "form"],
        "list": {
            "columns": [
                {"key": "name",             "label": "Tytuł"},
                {"key": "expected_revenue", "label": "Przychód"},
                {"key": "probability",      "label": "Prawdopodob."},
                {"key": "close_date",       "label": "Data zamknięcia"},
            ],
        },
        "kanban": {
            "groups_resource": "crm/stage",
            "group_field":     "stage_id",
            "title_field":     "name",
            "subtitle_fields": [
                {"key": "expected_revenue", "label": "Przychód"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",             "label": "Tytuł",           "type": "text", "required": True},
                {"key": "customer_id",      "label": "Klient",          "type": "select",
                 "options_resource": "crm/customer", "option_label": "name"},
                {"key": "pipeline_id",      "label": "Pipeline",        "type": "select",
                 "options_resource": "crm/pipeline", "option_label": "name"},
                {"key": "stage_id",         "label": "Etap",            "type": "select",
                 "options_resource": "crm/stage", "option_label": "name"},
                {"key": "expected_revenue", "label": "Spodziewany przychód", "type": "number"},
                {"key": "probability",      "label": "Prawdopodobieństwo (%)", "type": "number"},
                {"key": "close_date",       "label": "Data zamknięcia", "type": "date"},
                {"key": "description",      "label": "Opis",            "type": "textarea"},
            ],
        },
    },

    "crm.pipeline": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",          "label": "Nazwa"},
                {"key": "currency_code", "label": "Waluta"},
                {"key": "is_default",    "label": "Domyślny"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",          "label": "Nazwa",    "type": "text",    "required": True},
                {"key": "description",   "label": "Opis",     "type": "textarea"},
                {"key": "currency_code", "label": "Waluta",   "type": "text"},
                {"key": "is_default",    "label": "Domyślny", "type": "boolean"},
            ],
        },
    },

    "crm.stage": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",        "label": "Nazwa"},
                {"key": "sequence",    "label": "Kolejność"},
                {"key": "probability", "label": "Prawdopodob."},
                {"key": "is_won",      "label": "Wygrana"},
                {"key": "is_lost",     "label": "Przegrana"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",        "label": "Nazwa",             "type": "text",    "required": True},
                {"key": "pipeline_id", "label": "Pipeline",          "type": "select",
                 "options_resource": "crm/pipeline", "option_label": "name"},
                {"key": "sequence",    "label": "Kolejność",         "type": "number"},
                {"key": "probability", "label": "Prawdopodobieństwo", "type": "number"},
                {"key": "is_won",      "label": "Etap wygranej",     "type": "boolean"},
                {"key": "is_lost",     "label": "Etap przegranej",   "type": "boolean"},
                {"key": "fold",        "label": "Zwinięty w kanban", "type": "boolean"},
            ],
        },
    },
}
