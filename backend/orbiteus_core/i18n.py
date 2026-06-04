"""UI language and timezone helpers (shared backend validation)."""
from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SUPPORTED_UI_LANGUAGES = frozenset({"en"})
DEFAULT_UI_LANGUAGE = "en"

COMMON_TIMEZONES = (
    "UTC",
    "Europe/Warsaw",
    "Europe/Berlin",
    "Europe/Paris",
    "Europe/London",
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "Asia/Tokyo",
    "Asia/Singapore",
    "Australia/Sydney",
)


def normalize_ui_language(
    value: str | None,
    *,
    fallback: str = DEFAULT_UI_LANGUAGE,
    extra_codes: frozenset[str] | set[str] | None = None,
) -> str:
    raw = (value or "").strip().lower()
    if extra_codes and raw in extra_codes:
        return raw
    if raw in SUPPORTED_UI_LANGUAGES:
        return raw
    for prefix, code in (("pl", "pl"), ("de", "de"), ("fr", "fr"), ("en", "en")):
        if raw.startswith(prefix) and _code_allowed(code, extra_codes):
            return code
    return fallback


def _code_allowed(code: str, extra_codes: frozenset[str] | set[str] | None) -> bool:
    if extra_codes is not None:
        return code in extra_codes
    return code in SUPPORTED_UI_LANGUAGES


def normalize_timezone(value: str | None, *, fallback: str = "UTC") -> str:
    raw = (value or "").strip()
    if not raw:
        return fallback
    try:
        ZoneInfo(raw)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {raw}") from exc
    return raw


LANGUAGE_LABELS = {
    "en": "English",
    "pl": "Polski",
    "de": "Deutsch",
    "fr": "Français",
}


def language_select_options() -> list[dict[str, str]]:
    try:
        from orbiteus_core.i18n_registry import language_select_options as registered_options

        return registered_options()
    except Exception:
        return [{"value": code, "label": LANGUAGE_LABELS[code]} for code in sorted(SUPPORTED_UI_LANGUAGES)]


def timezone_select_options() -> list[dict[str, str]]:
    return [{"value": tz, "label": tz} for tz in COMMON_TIMEZONES]
