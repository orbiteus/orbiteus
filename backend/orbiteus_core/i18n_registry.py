"""In-memory UI translation registry (module files + DB overrides)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.i18n import (
    DEFAULT_UI_LANGUAGE,
    LANGUAGE_LABELS,
    SUPPORTED_UI_LANGUAGES,
    normalize_ui_language,
)

_file_by_lang: dict[str, dict[str, str]] = {}
_locale_meta: dict[str, dict[str, str]] = {}
_locale_owner: dict[str, str] = {}
_db_cache: dict[str, dict[str, str]] = {}
_merged_messages_cache: dict[str, tuple[str, dict[str, str]]] = {}
_MERGED_CACHE_MAX_LANGS = 16


def clear_ui_translation_cache() -> None:
    _db_cache.clear()
    _merged_messages_cache.clear()


def _enabled_map_signature(enabled_map: dict[str, bool] | None) -> str:
    if not enabled_map:
        return "default"
    return "|".join(f"{name}={'1' if enabled_map[name] else '0'}" for name in sorted(enabled_map))


def reset_i18n_registry_for_tests() -> None:
    """Test-only: drop in-memory catalogs (app must re-bootstrap for production)."""
    _file_by_lang.clear()
    _locale_meta.clear()
    _locale_owner.clear()
    clear_ui_translation_cache()


def register_module_messages(module: str, lang: str, messages: dict[str, str]) -> None:
    """Merge module file catalog; later modules override on duplicate keys."""
    bucket = _file_by_lang.setdefault(lang, {})
    bucket.update(messages)
    slug = module.strip().lower()
    if lang == DEFAULT_UI_LANGUAGE:
        _locale_owner[lang] = "base"
    elif slug:
        _locale_owner[lang] = slug


def register_locale_meta(entries: list[dict[str, str]], *, module: str = "") -> None:
    slug = module.strip().lower()
    for entry in entries:
        code = entry["code"]
        _locale_meta[code] = {
            "code": code,
            "label": entry["label"],
            "dayjs": entry.get("dayjs", code),
        }
        if slug and code != DEFAULT_UI_LANGUAGE:
            _locale_owner.setdefault(code, slug)


def _is_language_active(lang: str, enabled_map: dict[str, bool] | None) -> bool:
    if lang == DEFAULT_UI_LANGUAGE:
        return True
    owner = _locale_owner.get(lang, "")
    if not owner:
        return True
    if owner == "base":
        return lang == DEFAULT_UI_LANGUAGE
    from orbiteus_core.module_catalog import is_module_enabled

    return is_module_enabled(owner, enabled_map)


def registered_language_codes() -> frozenset[str]:
    """All languages loaded at bootstrap (ignores module enable flags)."""
    codes = set(SUPPORTED_UI_LANGUAGES) | set(_file_by_lang) | set(_locale_meta)
    return frozenset(codes)


def active_language_codes(enabled_map: dict[str, bool] | None = None) -> frozenset[str]:
    """Languages exposed in API / user profile when optional modules are disabled."""
    codes = {DEFAULT_UI_LANGUAGE}
    for lang in set(_file_by_lang) | set(_locale_meta):
        if _is_language_active(lang, enabled_map):
            codes.add(lang)
    return frozenset(codes)


def language_select_options(enabled_map: dict[str, bool] | None = None) -> list[dict[str, str]]:
    labels = dict(LANGUAGE_LABELS)
    for code, meta in _locale_meta.items():
        labels[code] = meta["label"]
    codes = active_language_codes(enabled_map)
    return [{"value": c, "label": labels.get(c, c)} for c in sorted(codes)]


def normalize_registered_language(
    value: str | None,
    *,
    fallback: str = DEFAULT_UI_LANGUAGE,
    enabled_map: dict[str, bool] | None = None,
) -> str:
    return normalize_ui_language(
        value,
        fallback=fallback,
        extra_codes=active_language_codes(enabled_map),
    )


def file_catalog_for(lang: str) -> dict[str, str]:
    return dict(_file_by_lang.get(lang, {}))


def catalog_with_en_fallback(lang: str) -> dict[str, str]:
    """Merge module file catalogs; non-English locales inherit missing keys from en."""
    en = file_catalog_for(DEFAULT_UI_LANGUAGE)
    if lang == DEFAULT_UI_LANGUAGE:
        return dict(en)
    locale = file_catalog_for(lang)
    return {**en, **locale}


async def db_overrides_for(session: AsyncSession, lang: str) -> dict[str, str]:
    if lang in _db_cache:
        return _db_cache[lang]
    from modules.base.model.mapping import base_ui_translations_table

    stmt = select(
        base_ui_translations_table.c.msg_key,
        base_ui_translations_table.c.value,
    ).where(base_ui_translations_table.c.lang == lang)
    rows = (await session.execute(stmt)).all()
    merged = {row.msg_key: row.value for row in rows}
    _db_cache[lang] = merged
    return merged


async def merged_messages_for(
    session: AsyncSession | None,
    lang: str,
    *,
    enabled_map: dict[str, bool] | None = None,
) -> dict[str, str]:
    """Module i18n files (en canonical) + DB overrides (DB wins)."""
    lang = normalize_registered_language(lang, enabled_map=enabled_map)
    sig = _enabled_map_signature(enabled_map)
    cached = _merged_messages_cache.get(lang)
    if cached and cached[0] == sig:
        out = dict(cached[1])
    else:
        out = catalog_with_en_fallback(lang)
        if len(_merged_messages_cache) >= _MERGED_CACHE_MAX_LANGS:
            _merged_messages_cache.clear()
        _merged_messages_cache[lang] = (sig, dict(out))
    if session is not None:
        out = {**out, **(await db_overrides_for(session, lang))}
    return out


def require_base_english_catalog() -> None:
    """Fail fast when base module did not load en.json."""
    en = file_catalog_for(DEFAULT_UI_LANGUAGE)
    if not en:
        raise RuntimeError(
            "UI i18n: modules/base/i18n/en.json produced an empty catalog — "
            "check manifest i18n and registry bootstrap",
        )
    if "common.save" not in en:
        raise RuntimeError("UI i18n: en catalog missing required key common.save")


def locales_payload(enabled_map: dict[str, bool] | None = None) -> list[dict[str, str]]:
    opts = language_select_options(enabled_map)
    rows: list[dict[str, str]] = []
    for o in opts:
        code = o["value"]
        owner = _locale_owner.get(code, "base" if code == DEFAULT_UI_LANGUAGE else "")
        rows.append(
            {
                "code": code,
                "label": o["label"],
                "dayjs": _locale_meta.get(code, {}).get("dayjs", code),
                "source": "core" if code == DEFAULT_UI_LANGUAGE else "module",
                "module": owner or ("base" if code == DEFAULT_UI_LANGUAGE else ""),
            },
        )
    return rows
