# Base module UI translations

**English only** ships here (`en.json`). Polish, German, French, and any other
locale belong in **separate modules** (reference pack: `modules/locales`).

## Files

| File | Role |
|------|------|
| `i18n/en.json` | Canonical UI message catalog (required) |

## Manifest

```python
"i18n": ["en"],
"i18n_locales": [
    {"code": "en", "label": "English", "dayjs": "en"},
],
```

## Adding keys

1. Add the key and English copy to `en.json`.
2. Mirror the key in each installed locale module (e.g. `modules/locales/i18n/pl.json`).
3. Run `python3 scripts/check_i18n.py` from the repo root.

## New language module

1. Create `backend/modules/<name>/i18n/<code>.json`.
2. Declare `i18n` and `i18n_locales` in `manifest.py`; `depends_on: ["base"]`.
3. Register the module in `backend/api.py` (`registry.register("<name>")`).
4. Restart the backend.

Flat keys (recommended):

```json
{
  "common.save": "Save",
  "nav.dashboard": "Dashboard"
}
```

## Merge order

1. `modules/base/i18n/en.json` (canonical fallback for missing keys)
2. Other modules’ `i18n/{lang}.json` (registry load order; later wins)
3. `base.ui-translation` rows (highest priority)

The SPA loads the merged catalog from `GET /api/base/i18n/messages/{lang}`.
