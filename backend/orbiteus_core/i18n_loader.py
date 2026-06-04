"""Load UI message catalogs from module ``i18n/`` directories."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _flatten_messages(raw: Any, prefix: str = "") -> dict[str, str]:
    """Accept flat or nested JSON objects; nested keys join with dots."""
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key, value in raw.items():
        full = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            out.update(_flatten_messages(value, full))
        elif value is not None:
            out[full] = str(value)
    return out


def load_json_catalog(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and "messages" in data and isinstance(data["messages"], dict):
        return _flatten_messages(data["messages"])
    return _flatten_messages(data)


def discover_module_i18n(module_path: Path, manifest: dict[str, Any]) -> list[tuple[str, str, dict[str, str]]]:
    """Return [(module_name, lang, messages), ...] from manifest hints."""
    results: list[tuple[str, str, dict[str, str]]] = []
    module_name = manifest.get("name") or module_path.name
    i18n_dir = module_path / "i18n"
    if not i18n_dir.is_dir():
        return results

    explicit_langs = manifest.get("i18n") or []
    for lang in explicit_langs:
        path = i18n_dir / f"{lang}.json"
        if path.is_file():
            try:
                results.append((module_name, lang, load_json_catalog(path)))
            except Exception as exc:
                logger.error("Failed to load %s: %s", path, exc)
                raise

    for rel in manifest.get("i18n_files") or []:
        path = module_path / rel
        if not path.is_file():
            logger.warning("Module '%s': i18n file not found: %s", module_name, path)
            continue
        stem = path.stem.split(".")[0]
        lang = stem if len(stem) <= 5 else stem
        try:
            results.append((module_name, lang, load_json_catalog(path)))
        except Exception as exc:
            logger.error("Failed to load %s: %s", path, exc)
            raise

    if not explicit_langs and not manifest.get("i18n_files"):
        for path in sorted(i18n_dir.glob("*.json")):
            lang = path.stem
            try:
                results.append((module_name, lang, load_json_catalog(path)))
            except Exception as exc:
                logger.error("Failed to load %s: %s", path, exc)
                raise

    return results


def parse_locale_meta(manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Optional manifest ``i18n_locales``: [{code, label, dayjs?}, ...]."""
    raw = manifest.get("i18n_locales") or []
    out: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        code = str(entry.get("code", "")).strip().lower()
        label = str(entry.get("label", "")).strip()
        if not code or not label:
            continue
        row: dict[str, str] = {"code": code, "label": label}
        if entry.get("dayjs"):
            row["dayjs"] = str(entry["dayjs"])
        out.append(row)
    return out
