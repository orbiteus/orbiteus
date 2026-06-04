"""Base module — declarative AI surface for engine administration."""
from orbiteus_core.ai.config import AIModuleConfig

AI = AIModuleConfig(
    enabled=True,
    system_prompt=(
        "You assist Orbiteus administrators with companies, users, roles, "
        "and engine configuration. Never bypass RBAC."
    ),
    accessible_models=[
        "base.company",
        "base.user",
        "base.role",
    ],
    embed_models=[
        "base.company",
        "base.user",
    ],
    dashboard=True,
)
