"""Legacy import path — canonical tables live in ``modules.base.model.mapping``.

Does **not** re-run ``register_model``; runtime registration happens only in
``modules.base.model.mapping._register_auto_crud()``.
"""
from modules.base.model.mapping import *  # noqa: F403
