"""Auth module manifest."""

MANIFEST = {
    "name": "Authentication",
    "version": "1.0.0",
    "depends_on": ["base"],
    "models": [],  # No auto-CRUD models – uses base.user
    "category": "Core",
    "auto_install": True,
}
