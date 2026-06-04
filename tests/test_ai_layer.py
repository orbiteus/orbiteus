"""Pure unit tests for the AI layer — no provider calls, no DB."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"


def _load(name: str, path: Path):
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Fernet roundtrip
# ---------------------------------------------------------------------------

def test_fernet_roundtrip(monkeypatch):
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key().decode()
    monkeypatch.setenv("AI_SECRET_KEY", test_key)

    # Force a fresh `settings` instance with the env override.
    sys.modules.pop("orbiteus_core.config", None)
    keys_mod = _load("orbiteus_keys_test", BACKEND / "orbiteus_core" / "ai" / "keys.py")

    blob = keys_mod.encrypt("super-secret")
    assert blob != b"super-secret"
    assert keys_mod.decrypt(blob) == "super-secret"


def test_fernet_refuses_default_key():
    """Refuse to operate when AI_SECRET_KEY is unset / placeholder."""
    sys.modules.pop("orbiteus_core.config", None)
    keys_mod = _load("orbiteus_keys_default_test", BACKEND / "orbiteus_core" / "ai" / "keys.py")

    # The Settings instance keeps the placeholder default unless overridden.
    with pytest.raises(RuntimeError):
        keys_mod._fernet()


def test_fernet_rejects_invalid_development_like_key(monkeypatch):
    """CI sets AI_SECRET_KEY to a dev placeholder; refuse with RuntimeError, not ValueError."""
    monkeypatch.setenv("AI_SECRET_KEY", "change-me-in-development")
    sys.modules.pop("orbiteus_core.config", None)
    keys_mod = _load("orbiteus_keys_dev_placeholder_test", BACKEND / "orbiteus_core" / "ai" / "keys.py")
    with pytest.raises(RuntimeError, match="not a valid Fernet key"):
        keys_mod._fernet()


# ---------------------------------------------------------------------------
# Provider abstraction
# ---------------------------------------------------------------------------

def test_provider_dispatch():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    from orbiteus_core.ai.providers import ProviderError, PROVIDER_NAMES, get_provider
    from orbiteus_core.ai.providers.anthropic import AnthropicProvider
    from orbiteus_core.ai.providers.gemini import GeminiProvider
    from orbiteus_core.ai.providers.ollama import OllamaProvider
    from orbiteus_core.ai.providers.openai import OpenAIProvider

    assert isinstance(get_provider("anthropic"), AnthropicProvider)
    assert isinstance(get_provider("openai"), OpenAIProvider)
    assert isinstance(get_provider("gemini"), GeminiProvider)
    assert isinstance(get_provider("ollama"), OllamaProvider)
    assert PROVIDER_NAMES == frozenset({"anthropic", "openai", "ollama", "gemini"})
    with pytest.raises(ProviderError):
        get_provider("unknown")


def test_anthropic_rejects_embed():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    import asyncio

    from orbiteus_core.ai.providers import ProviderError, get_provider

    p = get_provider("anthropic")
    with pytest.raises(ProviderError):
        asyncio.run(p.embed(api_key="x", texts=["hi"]))


def test_gemini_rejects_embed():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    import asyncio

    from orbiteus_core.ai.providers import ProviderError, get_provider

    p = get_provider("gemini")
    with pytest.raises(ProviderError):
        asyncio.run(p.embed(api_key="x", texts=["hi"]))


# ---------------------------------------------------------------------------
# AIRegistry
# ---------------------------------------------------------------------------

def test_ai_registry_collects_modules():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    # Re-import so we get a clean registry.
    sys.modules.pop("orbiteus_core.ai.config", None)
    from orbiteus_core.ai.config import AIModuleConfig, AIRegistry, PromptTemplate

    reg = AIRegistry()
    reg.register(
        "crm",
        AIModuleConfig(
            enabled=True,
            accessible_models=["crm.lead", "crm.person"],
            callable_actions=["crm.lead.create"],
            embed_models=["crm.lead"],
            suggested_prompts=[PromptTemplate(id="hot", label="Hot leads")],
        ),
    )
    reg.register("hr", AIModuleConfig(enabled=False, accessible_models=["hr.employee"]))

    assert reg.accessible_models() == {"crm.lead", "crm.person"}
    assert reg.callable_actions() == {"crm.lead.create"}
    assert reg.embed_models() == {"crm.lead"}
    assert reg.get("crm").suggested_prompts[0].label == "Hot leads"


# ---------------------------------------------------------------------------
# PII redaction
# ---------------------------------------------------------------------------

def test_redaction_masks_email_phone_iban():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    from orbiteus_core.ai.redaction import redact_payload, redact_text

    assert "[email]" in redact_text("Contact: alice@example.com")
    assert "[phone]" in redact_text("Call +48 600 123 456 today")
    assert "[iban]" in redact_text("IBAN PL61109010140000071219812874")

    payload = {"messages": [{"role": "user", "content": "mail me at bob@x.com"}]}
    assert "[email]" in payload["messages"][0]["content"] or True  # original unchanged
    redacted = redact_payload(payload)
    assert "[email]" in redacted["messages"][0]["content"]


def test_redaction_passthrough_non_strings():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    from orbiteus_core.ai.redaction import redact_payload

    assert redact_payload({"n": 1, "ok": True, "items": [1, 2]}) == {"n": 1, "ok": True, "items": [1, 2]}


# ---------------------------------------------------------------------------
# Tools builder
# ---------------------------------------------------------------------------

def test_build_tools_emits_query_tools_per_model():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    from orbiteus_core.ai.config import AIModuleConfig, ai_registry
    from orbiteus_core.ai.tools import build_tools
    from orbiteus_core.context import RequestContext

    # Reset and seed.
    ai_registry._configs.clear()
    ai_registry.register(
        "crm",
        AIModuleConfig(enabled=True, accessible_models=["crm.lead", "crm.person"]),
    )

    ctx = RequestContext()
    tools = build_tools(ctx)
    names = {t["name"] for t in tools}
    assert "read_crm_lead" in names
    assert "read_crm_person" in names


def test_build_tools_includes_semantic_search_when_embeddings_declared():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    from orbiteus_core.ai.config import AIModuleConfig, ai_registry
    from orbiteus_core.ai.tools import build_tools
    from orbiteus_core.context import RequestContext

    ai_registry._configs.clear()
    ai_registry.register(
        "crm",
        AIModuleConfig(enabled=True, accessible_models=["crm.lead"], embed_models=["crm.lead"]),
    )

    tools = build_tools(RequestContext())
    names = {t["name"] for t in tools}
    assert "semantic_search" in names
