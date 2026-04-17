"""Auth module — Action declarations for Command Palette."""
from orbiteus_core.ai import Action, ActionCategory

ACTIONS = [
    Action(
        id="auth.logout",
        label="Log Out",
        keywords=[
            # EN
            "logout", "log out", "sign out", "exit", "end session",
            # PL
            "wyloguj", "wyloguj się", "wyjdź", "zakończ sesję",
        ],
        description="End session and go to login page",
        category=ActionCategory.EXECUTE,
        target="navigate",
        target_url="/login",
        icon="logout",
    ),
    Action(
        id="auth.profile",
        label="My Profile",
        keywords=[
            # EN
            "profile", "my account", "account settings", "my profile",
            # PL
            "profil", "mój profil", "moje konto", "ustawienia konta",
        ],
        description="View and edit your user profile",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/profile",
        icon="user-circle",
    ),
]
