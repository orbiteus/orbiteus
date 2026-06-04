"""Base module – admin-ui view configuration.

System / admin screens: Users, Companies, Partners, engine system objects.

Note: this static dictionary is a legacy hint format that pre-dates the
registry-driven `GET /api/base/ui-config` builder. The Admin UI catch-all
routes (`[module]/[model]`) read the dynamic config; this file is kept for
parity and any tooling that imports `view_config` declared in the module
manifest.
"""
from __future__ import annotations

UI_CONFIG = {
    "base.user": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",          "label": "Full name"},
                {"key": "email",         "label": "Email"},
                {"key": "last_login",    "label": "Last login", "widget": "last_login"},
                {"key": "role_ids",      "label": "Roles"},
                {"key": "is_active",     "label": "Active"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",     "label": "Full name", "type": "text",  "required": True},
                {"key": "email",    "label": "Email",     "type": "email", "required": True},
                {"key": "password", "label": "Password",  "type": "text"},
                {"key": "company_ids", "label": "Companies", "type": "tags"},
                {"key": "role_ids", "label": "Roles",     "type": "tags"},
                {"key": "language", "label": "Language",  "type": "select",
                 "options": [
                     {"value": "en", "label": "English"},
                     {"value": "pl", "label": "Polski"},
                 ]},
                {"key": "timezone", "label": "Time zone", "type": "text"},
                {"key": "is_active", "label": "Active",   "type": "boolean"},
            ],
        },
    },

    "base.company": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",          "label": "Name"},
                {"key": "currency_code", "label": "Currency"},
                {"key": "country_code",  "label": "Country"},
                {"key": "city",          "label": "City"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",          "label": "Name",         "type": "text",  "required": True},
                {"key": "currency_code", "label": "Currency",     "type": "text"},
                {"key": "country_code",  "label": "Country",      "type": "text"},
                {"key": "vat",           "label": "VAT number",   "type": "text"},
                {"key": "email",         "label": "Email",        "type": "email"},
                {"key": "phone",         "label": "Phone",        "type": "tel"},
                {"key": "street",        "label": "Street",       "type": "text"},
                {"key": "city",          "label": "City",         "type": "text"},
                {"key": "zip_code",      "label": "Postal code",  "type": "text"},
            ],
        },
    },

    "base.role": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",        "label": "Name"},
                {"key": "code",        "label": "Technical code"},
                {"key": "is_system",   "label": "System"},
                {"key": "description", "label": "Description"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",        "label": "Name",            "type": "text",     "required": True},
                {"key": "code",        "label": "Technical code",  "type": "text",     "required": True},
                {"key": "description", "label": "Description",     "type": "textarea"},
            ],
        },
    },

    "base.agent": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "name",          "label": "Name"},
                {"key": "slug",          "label": "Slug"},
                {"key": "module_scope",  "label": "Module"},
                {"key": "is_system",     "label": "System"},
                {"key": "active",        "label": "Active"},
            ],
        },
        "form": {
            "fields": [
                {"key": "name",            "label": "Name",           "type": "text",     "required": True},
                {"key": "slug",            "label": "Slug",           "type": "text",     "required": True},
                {"key": "module_scope",    "label": "Module scope",   "type": "text"},
                {"key": "system_prompt",   "label": "System prompt",  "type": "textarea"},
                {"key": "allowed_models",  "label": "Allowed models", "type": "tags"},
                {"key": "allowed_actions", "label": "Allowed actions","type": "tags"},
                {"key": "can_delegate",      "label": "Can delegate",   "type": "boolean"},
                {"key": "allowed_delegate_slugs", "label": "Delegate slugs", "type": "tags"},
                {"key": "schedule_interval_minutes", "label": "Schedule (minutes)", "type": "number"},
                {"key": "schedule_prompt",   "label": "Schedule prompt", "type": "textarea"},
                {"key": "provider",        "label": "Provider",       "type": "text"},
                {"key": "model_default",   "label": "Default model",  "type": "text"},
                {"key": "active",          "label": "Active",         "type": "boolean"},
            ],
        },
    },

    "base.agent-run": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "agent_id",     "label": "Agent"},
                {"key": "parent_run_id","label": "Parent run"},
                {"key": "depth",        "label": "Depth"},
                {"key": "status",       "label": "Status"},
                {"key": "tokens_used",  "label": "Tokens"},
                {"key": "input_prompt", "label": "Prompt"},
                {"key": "create_date",  "label": "Started"},
            ],
        },
        "form": {
            "fields": [
                {"key": "agent_id",             "label": "Agent",        "type": "text", "readonly": True},
                {"key": "status",               "label": "Status",       "type": "text", "readonly": True},
                {"key": "input_prompt",         "label": "Prompt",       "type": "textarea", "readonly": True},
                {"key": "output_text",          "label": "Output",       "type": "textarea", "readonly": True},
                {"key": "tokens_used",          "label": "Tokens used",  "type": "number", "readonly": True},
                {"key": "error_message",        "label": "Error",        "type": "textarea", "readonly": True},
            ],
        },
    },

    "base.config-param": {
        "views": ["list", "form"],
        "list": {
            "columns": [
                {"key": "key",         "label": "Key"},
                {"key": "value",       "label": "Value"},
                {"key": "description", "label": "Description"},
            ],
        },
        "form": {
            "fields": [
                {"key": "key",         "label": "Key",         "type": "text", "required": True},
                {"key": "value",       "label": "Value",       "type": "text"},
                {"key": "description", "label": "Description", "type": "textarea"},
            ],
        },
    },
}
