"""CRM module – RBAC access rights and record rules."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

CRM_ACCESS_RIGHTS = [
    # Sales manager – full access to CRM
    *[
        {
            "role_name": "crm.group_crm_manager",
            "model_name": model,
            "perm_read": True,
            "perm_write": True,
            "perm_create": True,
            "perm_unlink": True,
        }
        for model in ["crm.customer", "crm.opportunity", "crm.pipeline", "crm.stage"]
    ],
    # Salesman – can create/edit, but sees only their own opportunities (record rule below)
    *[
        {
            "role_name": "crm.group_crm_user",
            "model_name": model,
            "perm_read": True,
            "perm_write": True,
            "perm_create": True,
            "perm_unlink": False,
        }
        for model in ["crm.customer", "crm.opportunity"]
    ],
    {
        "role_name": "crm.group_crm_user",
        "model_name": "crm.pipeline",
        "perm_read": True,
        "perm_write": False,
        "perm_create": False,
        "perm_unlink": False,
    },
    {
        "role_name": "crm.group_crm_user",
        "model_name": "crm.stage",
        "perm_read": True,
        "perm_write": False,
        "perm_create": False,
        "perm_unlink": False,
    },
]

CRM_RECORD_RULES = [
    {
        "name": "crm_opportunity_salesman",
        "model_name": "crm.opportunity",
        "roles": ["crm.group_crm_user"],
        "global": False,
        # Salesman sees only their own opportunities
        "domain": [("assigned_user_id", "=", "current_user")],
    }
]


def setup() -> None:
    """Merge CRM access rights into RBAC cache."""
    from orbiteus_core.security import rbac

    rbac._model_access.update(
        {
            entry["role_name"]: {
                **rbac._model_access.get(entry["role_name"], {}),
                entry["model_name"]: {
                    "read": entry["perm_read"],
                    "write": entry["perm_write"],
                    "create": entry["perm_create"],
                    "unlink": entry["perm_unlink"],
                },
            }
            for entry in CRM_ACCESS_RIGHTS
        }
    )

    for rule in CRM_RECORD_RULES:
        rbac._record_rules.setdefault(rule["model_name"], []).append(rule)

    logger.info("CRM security loaded: %d access entries, %d rules",
                len(CRM_ACCESS_RIGHTS), len(CRM_RECORD_RULES))
