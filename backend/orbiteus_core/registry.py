"""ModuleRegistry – the heart of Orbiteus auto-propagation engine.

Lifecycle per module registration:
  1. discover()         – import module package, read manifest.py
  2. validate_deps()    – topological sort, ensure all depends_on are registered
  3. load_mappings()    – call module.model.mapping.setup() → SQLAlchemy Tables registered
  4. register_security()– load security/access.yaml (YAML) OR controller.security.setup() (legacy)
  5. register_routes()  – auto-generate CRUD routers + attach module.controller.router
  6. register_menus()   – seed base_ui_menus entries

Usage in api.py:
    from orbiteus_core.registry import registry
    from fastapi import FastAPI

    app = FastAPI()
    registry.register("base")
    registry.register("auth")
    registry.bootstrap(app)
"""
from __future__ import annotations

import importlib
import logging
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from types import ModuleType
from typing import Any

from fastapi import FastAPI

from orbiteus_core.exceptions import DependencyError, ModuleNotFound

logger = logging.getLogger(__name__)


class ModuleDescriptor:
    """Holds a registered module's manifest and imported package."""

    def __init__(self, name: str, package: ModuleType, manifest: dict[str, Any]) -> None:
        self.name = name
        self.package = package
        self.manifest = manifest

    @property
    def depends_on(self) -> list[str]:
        return self.manifest.get("depends_on", [])

    @property
    def models(self) -> list[str]:
        return self.manifest.get("models", [])

    def __repr__(self) -> str:
        return f"<Module {self.name} v{self.manifest.get('version', '?')}>"


class ModuleRegistry:
    """Central registry for all Orbiteus modules."""

    def __init__(self) -> None:
        self._modules: dict[str, ModuleDescriptor] = {}
        self._load_order: list[str] = []
        self._bootstrapped = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, module_name: str) -> None:
        """Register a module by name (must be importable as modules.<name>)."""
        if module_name in self._modules:
            logger.debug("Module '%s' already registered, skipping.", module_name)
            return

        package = self._import_module(module_name)
        manifest = self._load_manifest(module_name, package)
        descriptor = ModuleDescriptor(module_name, package, manifest)
        self._modules[module_name] = descriptor
        logger.info("Registered module: %s", descriptor)

    def bootstrap(self, app: FastAPI) -> None:
        """Execute the full module lifecycle and attach routers to the FastAPI app."""
        if self._bootstrapped:
            raise RuntimeError("ModuleRegistry.bootstrap() called more than once")

        self._resolve_load_order()

        for name in self._load_order:
            desc = self._modules[name]
            logger.info("Loading module: %s", name)
            self._load_mappings(desc)

        for name in self._load_order:
            desc = self._modules[name]
            self._register_security(desc)
            self._load_views(desc)
            self._register_actions(desc)
            self._register_ai(desc)
            self._register_routes(app, desc)
            self._register_menus(desc)

        for name in self._load_order:
            self._load_i18n(self._modules[name])

        from orbiteus_core.i18n_registry import require_base_english_catalog

        require_base_english_catalog()

        self._bootstrapped = True
        logger.info(
            "Orbiteus bootstrap complete. Loaded modules: %s",
            ", ".join(self._load_order),
        )

    def get_module(self, name: str) -> ModuleDescriptor:
        if name not in self._modules:
            raise ModuleNotFound(name)
        return self._modules[name]

    async def seed_security_to_db(self) -> None:
        """Persist YAML-sourced security configs to base_model_access + base_rules tables.

        Called once from FastAPI startup event (after DB is reachable).
        Idempotent – upserts existing records.
        """
        from orbiteus_core.context import RequestContext
        from orbiteus_core.db import AsyncSessionFactory
        from orbiteus_core.security_loader import seed_security_to_db

        ctx = RequestContext(is_superadmin=True)
        async with AsyncSessionFactory() as session:
            for name in self._load_order:
                desc = self._modules[name]
                config = getattr(desc, "_security_config", None)
                if config is None:
                    continue
                try:
                    await seed_security_to_db(config, session, ctx)
                except Exception as e:
                    logger.warning("Could not seed security to DB for '%s': %s", name, e)
            await session.commit()
        logger.info("Security seeded to DB for all YAML modules.")

    async def seed_views_to_db(self) -> None:
        """Persist view definitions (JSON primary, XML legacy) to base_ui_views.

        Called once from FastAPI startup event (after DB is reachable).
        Idempotent – upserts existing views by name.
        """
        from orbiteus_core.context import RequestContext
        from orbiteus_core.db import AsyncSessionFactory
        from orbiteus_core.json_views import seed_json_views_to_db
        from orbiteus_core.view_loader import seed_views_to_db

        ctx = RequestContext(is_superadmin=True)
        async with AsyncSessionFactory() as session:
            for name in self._load_order:
                desc = self._modules[name]
                json_views = getattr(desc, "_json_view_definitions", None)
                if json_views:
                    try:
                        await seed_json_views_to_db(json_views, name, session, ctx)
                    except Exception as e:
                        logger.warning(
                            "Could not seed JSON views to DB for '%s': %s", name, e,
                        )
                xml_views = getattr(desc, "_view_definitions", None)
                if xml_views:
                    try:
                        await seed_views_to_db(xml_views, session, ctx)
                    except Exception as e:
                        logger.warning(
                            "Could not seed XML views to DB for '%s': %s", name, e,
                        )
            await session.commit()
        logger.info("Views seeded to DB for all modules.")

    async def seed_registry_to_db(self) -> None:
        """Persist auto-CRUD model catalogue to base_models / base_model_fields."""
        from orbiteus_core.context import RequestContext
        from orbiteus_core.db import AsyncSessionFactory
        from orbiteus_core.registry_loader import seed_registry_to_db

        ctx = RequestContext(is_superadmin=True)
        async with AsyncSessionFactory() as session:
            try:
                await seed_registry_to_db(session, ctx)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.warning("Could not seed registry metadata to DB: %s", e)
                raise
        logger.info("Registry metadata seeded to DB.")

    def get_all_views(self) -> dict[str, Any]:
        """Return all registered view definitions as a flat dict keyed by view name."""
        result: dict[str, Any] = {}
        for name in self._load_order:
            desc = self._modules[name]
            for view in getattr(desc, "_view_definitions", []):
                result[view.name] = view
        return result

    def get_all_json_views(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Return JSON views keyed by model name then view type (list/form/…)."""
        from orbiteus_core.json_views import view_to_ui_payload

        result: dict[str, dict[str, dict[str, Any]]] = {}
        for name in self._load_order:
            desc = self._modules[name]
            for view in getattr(desc, "_json_view_definitions", []):
                result.setdefault(view.model, {})[view.type] = view_to_ui_payload(view)
        return result

    @property
    def loaded_modules(self) -> list[str]:
        return list(self._load_order)

    # ------------------------------------------------------------------
    # Internal lifecycle steps
    # ------------------------------------------------------------------

    def _import_module(self, module_name: str) -> ModuleType:
        try:
            return importlib.import_module(f"modules.{module_name}")
        except ImportError as e:
            raise ModuleNotFound(module_name) from e

    def _load_manifest(self, module_name: str, package: ModuleType) -> dict[str, Any]:
        try:
            manifest_mod = importlib.import_module(f"modules.{module_name}.manifest")
            manifest = getattr(manifest_mod, "MANIFEST")
        except (ImportError, AttributeError) as e:
            raise ModuleNotFound(module_name) from e

        # Support both ModuleManifest (Pydantic) and plain dict
        from orbiteus_core.manifest import ModuleManifest
        if isinstance(manifest, ModuleManifest):
            return manifest.to_dict()
        return manifest

    def _resolve_load_order(self) -> None:
        """Topological sort of all registered modules by depends_on."""
        graph: dict[str, set[str]] = {}
        for name, desc in self._modules.items():
            for dep in desc.depends_on:
                if dep not in self._modules:
                    raise DependencyError(name, dep)
            graph[name] = set(desc.depends_on)

        try:
            sorter = TopologicalSorter(graph)
            self._load_order = list(sorter.static_order())
        except CycleError as e:
            raise RuntimeError(f"Circular dependency detected in modules: {e}") from e

    def _load_mappings(self, desc: ModuleDescriptor) -> None:
        """Import module mapping to trigger SQLAlchemy Table registration.

        Tries MVC path (model.mapping) first, falls back to legacy flat path.
        """
        for candidate in (f"modules.{desc.name}.model.mapping", f"modules.{desc.name}.mapping"):
            try:
                mod = importlib.import_module(candidate)
                if hasattr(mod, "setup"):
                    mod.setup()
                return
            except ImportError:
                continue
        logger.debug("Module '%s' has no mapping – skipping.", desc.name)

    def _register_security(self, desc: ModuleDescriptor) -> None:
        """Load module security: YAML (primary) or legacy Python setup() (fallback).

        Priority:
          1. security/access.yaml  → parsed by security_loader, applied to RBAC cache
          2. controller.security.setup()  → legacy Python dict approach
          3. security.setup()  → legacy flat path
        """
        # 1. Try YAML (new canonical approach)
        yaml_path = self._module_path(desc) / "security" / "access.yaml"
        if yaml_path.exists():
            from orbiteus_core.security_loader import apply_security_to_cache, load_yaml_security
            try:
                config = load_yaml_security(yaml_path)
                apply_security_to_cache(config)
                # Store config on descriptor for later DB seeding (done async in startup)
                desc._security_config = config
                logger.info(
                    "Module '%s' security loaded from YAML: %d access, %d rules",
                    desc.name, len(config.access), len(config.record_rules),
                )
                return
            except Exception as e:
                logger.error("Failed to load security YAML for '%s': %s", desc.name, e)
                raise

        # 2. Legacy Python setup()
        _sec_candidates = (
            f"modules.{desc.name}.controller.security",
            f"modules.{desc.name}.security",
        )
        for candidate in _sec_candidates:
            try:
                mod = importlib.import_module(candidate)
                if hasattr(mod, "setup"):
                    mod.setup()
                return
            except ImportError:
                continue
        logger.debug("Module '%s' has no security – skipping.", desc.name)

    def _module_path(self, desc: ModuleDescriptor) -> Path:
        """Return filesystem path to the module package directory."""
        pkg_file = getattr(desc.package, "__file__", None)
        if pkg_file:
            return Path(pkg_file).parent
        # Fallback: assume modules/ directory next to this file
        return Path(__file__).parent.parent / "modules" / desc.name

    def _register_routes(self, app: FastAPI, desc: ModuleDescriptor) -> None:
        """Auto-generate CRUD router for every model + attach custom router.

        Tries MVC path (controller.router) first, falls back to legacy flat path.
        """
        from orbiteus_core.auto_router import build_crud_router

        for model_name in desc.models:
            router = build_crud_router(model_name)
            if router:
                app.include_router(router, prefix=f"/api/{model_name.replace('.', '/')}")
                logger.info("Auto-CRUD router mounted: /api/%s", model_name.replace(".", "/"))

        # Custom router – MVC: controller.router, legacy: router
        for candidate in (f"modules.{desc.name}.controller.router", f"modules.{desc.name}.router"):
            try:
                mod = importlib.import_module(candidate)
            except ImportError as e:
                logger.debug("Skip router candidate %s: %s", candidate, e)
                continue
            if hasattr(mod, "router"):
                app.include_router(mod.router, prefix=f"/api/{desc.name}")
                logger.info("Custom router mounted: /api/%s", desc.name)
                return
        if not desc.models:
            logger.warning(
                "Module '%s' has no models and no importable custom router "
                "(check optional dependencies, e.g. pyotp for auth).",
                desc.name,
            )

    def _load_views(self, desc: ModuleDescriptor) -> None:
        """Load JSON views (primary) and XML views (deprecated fallback) from manifest data[].

        JSON: `*.view.json` → desc._json_view_definitions
        XML:  `*.xml`       → desc._view_definitions (legacy)
        """
        from orbiteus_core.json_views import load_json_view
        from orbiteus_core.view_loader import load_xml_views

        data_files: list[str] = desc.manifest.get("data", [])
        json_files = [f for f in data_files if f.endswith(".view.json")]
        xml_files = [f for f in data_files if f.endswith(".xml")]

        if not json_files and not xml_files:
            return

        module_path = self._module_path(desc)

        if json_files:
            json_views = []
            for rel_path in json_files:
                json_path = module_path / rel_path
                try:
                    json_views.append(load_json_view(json_path, desc.name))
                except FileNotFoundError:
                    logger.warning(
                        "Module '%s': JSON view not found: %s", desc.name, json_path,
                    )
                except Exception as e:
                    logger.error(
                        "Module '%s': failed to load JSON view %s: %s",
                        desc.name, json_path, e,
                    )
                    raise
            if json_views:
                desc._json_view_definitions = json_views
                logger.info(
                    "Module '%s' loaded %d JSON view definitions",
                    desc.name, len(json_views),
                )

        if xml_files:
            all_views = []
            for rel_path in xml_files:
                xml_path = module_path / rel_path
                try:
                    all_views.extend(load_xml_views(xml_path, desc.name))
                except FileNotFoundError:
                    logger.warning(
                        "Module '%s': XML view not found: %s", desc.name, xml_path,
                    )
                except Exception as e:
                    logger.error(
                        "Module '%s': failed to load XML views from %s: %s",
                        desc.name, xml_path, e,
                    )
                    raise
            if all_views:
                desc._view_definitions = all_views
                logger.info(
                    "Module '%s' loaded %d legacy XML view definitions",
                    desc.name, len(all_views),
                )

    def _register_actions(self, desc: ModuleDescriptor) -> None:
        """Load actions.py from the module and register them in ActionRegistry.

        Looks for ACTIONS list in:
          modules.<name>.actions
        Skips gracefully if actions.py does not exist.
        """
        try:
            mod = importlib.import_module(f"modules.{desc.name}.actions")
        except ImportError:
            return

        actions = getattr(mod, "ACTIONS", None)
        if not actions:
            logger.debug("Module '%s' has no ACTIONS in actions.py — skipping.", desc.name)
            return

        from orbiteus_core.ai.registry import action_registry
        action_registry.register_module(desc.name, actions)

    def _register_ai(self, desc: ModuleDescriptor) -> None:
        """Load ai.py from the module and register AIModuleConfig."""
        try:
            mod = importlib.import_module(f"modules.{desc.name}.ai")
        except ImportError:
            return

        config = getattr(mod, "AI", None)
        if config is None:
            logger.debug("Module '%s' has no AI in ai.py — skipping.", desc.name)
            return

        from orbiteus_core.ai.config import ai_registry

        ai_registry.register(desc.name, config)
        logger.info(
            "Module '%s' registered AI config (%d accessible models)",
            desc.name,
            len(config.accessible_models),
        )

    def _register_menus(self, desc: ModuleDescriptor) -> None:
        """Seed base_ui_menus entries defined in the module manifest."""
        menus = desc.manifest.get("menus", [])
        if menus:
            logger.debug(
                "Module '%s' declares %d menu entries (deferred to DB).",
                desc.name,
                len(menus),
            )

    def _load_i18n(self, desc: ModuleDescriptor) -> None:
        """Load ``i18n/*.json`` catalogs and locale metadata from module manifest."""
        from orbiteus_core.i18n_loader import discover_module_i18n, parse_locale_meta
        from orbiteus_core.i18n_registry import register_locale_meta, register_module_messages

        module_path = self._module_path(desc)
        for _mod, lang, messages in discover_module_i18n(module_path, desc.manifest):
            register_module_messages(desc.name, lang, messages)
            logger.info(
                "Module '%s' registered %d UI messages for '%s'",
                desc.name,
                len(messages),
                lang,
            )
        meta = parse_locale_meta(desc.manifest)
        if meta:
            register_locale_meta(meta, module=desc.name)


# Singleton – import and use everywhere
registry = ModuleRegistry()
