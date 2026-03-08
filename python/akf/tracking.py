"""AKF auto-tracking — intercept LLM SDK calls to capture model/provider metadata.

Usage::

    import akf
    import openai

    client = akf.track(openai.OpenAI())
    response = client.chat.completions.create(model="gpt-4o", ...)

    # model/provider auto-populated
    unit = akf.create("claim", confidence=0.95)
    # unit.origin.model == "gpt-4o", unit.origin.provider == "openai"

Supported SDKs:
    - OpenAI (and OpenAI-compatible: Groq, Together, Perplexity)
    - Anthropic
    - Google Generative AI (google-generativeai)
    - Mistral (mistralai)
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Thread-local context
# ---------------------------------------------------------------------------

@dataclass
class _TrackingEntry:
    model: str
    provider: str
    timestamp: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


@dataclass
class _TrackingContext:
    last: Optional[_TrackingEntry] = None
    history: list = field(default_factory=list)
    max_history: int = 100


_ctx = threading.local()


def _get_ctx() -> _TrackingContext:
    if not hasattr(_ctx, "tracking"):
        _ctx.tracking = _TrackingContext()
    return _ctx.tracking


def _record(model: str, provider: str, input_tokens: int = None, output_tokens: int = None):
    entry = _TrackingEntry(
        model=model,
        provider=provider,
        timestamp=datetime.now(timezone.utc).isoformat(),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    ctx = _get_ctx()
    ctx.last = entry
    ctx.history.append(entry)
    if len(ctx.history) > ctx.max_history:
        ctx.history = ctx.history[-ctx.max_history:]


def get_last_model() -> Optional[dict]:
    """Return the last tracked model/provider as a dict, or None."""
    ctx = _get_ctx()
    if ctx.last is None:
        return None
    return {
        "model": ctx.last.model,
        "provider": ctx.last.provider,
        "timestamp": ctx.last.timestamp,
        "input_tokens": ctx.last.input_tokens,
        "output_tokens": ctx.last.output_tokens,
    }


def get_tracking_history() -> list[dict]:
    """Return all tracked LLM calls in this thread."""
    ctx = _get_ctx()
    return [
        {
            "model": e.model,
            "provider": e.provider,
            "timestamp": e.timestamp,
            "input_tokens": e.input_tokens,
            "output_tokens": e.output_tokens,
        }
        for e in ctx.history
    ]


def clear_tracking():
    """Reset tracking context for this thread."""
    ctx = _get_ctx()
    ctx.last = None
    ctx.history.clear()


# ---------------------------------------------------------------------------
# SDK detection & wrapping
# ---------------------------------------------------------------------------

def _detect_sdk(client: Any) -> str:
    """Detect which LLM SDK a client belongs to."""
    mod = type(client).__module__ or ""

    if "openai" in mod:
        return "openai"
    if "anthropic" in mod:
        return "anthropic"
    if "mistralai" in mod:
        return "mistral"
    if "google" in mod and "generative" in mod:
        return "google"

    raise TypeError(
        f"Unsupported client type: {type(client).__name__} (module: {mod}). "
        "Supported: OpenAI, Anthropic, Mistral, Google GenerativeAI."
    )


def track(client: Any, *, provider: str = None) -> Any:
    """Wrap an LLM client to auto-track model/provider on every call.

    Args:
        client: An LLM SDK client (OpenAI, Anthropic, Mistral, Google).
        provider: Override provider name (useful for OpenAI-compatible APIs
                  like Groq, Together, Perplexity, etc.).

    Returns:
        A wrapped client that behaves identically but records model metadata.
    """
    sdk = _detect_sdk(client)
    actual_provider = provider or sdk

    if sdk == "openai":
        return _wrap_openai(client, actual_provider)
    elif sdk == "anthropic":
        return _wrap_anthropic(client, actual_provider)
    elif sdk == "mistral":
        return _wrap_mistral(client, actual_provider)
    elif sdk == "google":
        return _wrap_google(client, actual_provider)
    else:
        raise TypeError(f"No tracker for SDK: {sdk}")


# ---------------------------------------------------------------------------
# OpenAI wrapper (also works for Groq, Together, etc.)
# ---------------------------------------------------------------------------

class _TrackedCompletions:
    """Wraps client.chat.completions to intercept create() calls."""

    def __init__(self, original, provider: str):
        self._original = original
        self._provider = provider

    def create(self, **kwargs):
        response = self._original.create(**kwargs)
        model = getattr(response, "model", None) or kwargs.get("model", "unknown")
        usage = getattr(response, "usage", None)
        _record(
            model=model,
            provider=self._provider,
            input_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
            output_tokens=getattr(usage, "completion_tokens", None) if usage else None,
        )
        return response

    def __getattr__(self, name):
        return getattr(self._original, name)


class _TrackedChat:
    def __init__(self, original_chat, provider: str):
        self._original = original_chat
        self._provider = provider
        self.completions = _TrackedCompletions(original_chat.completions, provider)

    def __getattr__(self, name):
        return getattr(self._original, name)


class _TrackedOpenAI:
    def __init__(self, client, provider: str):
        self._client = client
        self._provider = provider
        self.chat = _TrackedChat(client.chat, provider)

    def __getattr__(self, name):
        return getattr(self._client, name)


def _wrap_openai(client, provider: str):
    return _TrackedOpenAI(client, provider)


# ---------------------------------------------------------------------------
# Anthropic wrapper
# ---------------------------------------------------------------------------

class _TrackedAnthropicMessages:
    def __init__(self, original, provider: str):
        self._original = original
        self._provider = provider

    def create(self, **kwargs):
        response = self._original.create(**kwargs)
        model = getattr(response, "model", None) or kwargs.get("model", "unknown")
        usage = getattr(response, "usage", None)
        _record(
            model=model,
            provider=self._provider,
            input_tokens=getattr(usage, "input_tokens", None) if usage else None,
            output_tokens=getattr(usage, "output_tokens", None) if usage else None,
        )
        return response

    def __getattr__(self, name):
        return getattr(self._original, name)


class _TrackedAnthropic:
    def __init__(self, client, provider: str):
        self._client = client
        self._provider = provider
        self.messages = _TrackedAnthropicMessages(client.messages, provider)

    def __getattr__(self, name):
        return getattr(self._client, name)


def _wrap_anthropic(client, provider: str):
    return _TrackedAnthropic(client, provider)


# ---------------------------------------------------------------------------
# Mistral wrapper
# ---------------------------------------------------------------------------

class _TrackedMistral:
    def __init__(self, client, provider: str):
        self._client = client
        self._provider = provider

    def chat(self, **kwargs):
        response = self._client.chat(**kwargs)
        model = getattr(response, "model", None) or kwargs.get("model", "unknown")
        usage = getattr(response, "usage", None)
        _record(
            model=model,
            provider=self._provider,
            input_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
            output_tokens=getattr(usage, "completion_tokens", None) if usage else None,
        )
        return response

    def __getattr__(self, name):
        return getattr(self._client, name)


def _wrap_mistral(client, provider: str):
    return _TrackedMistral(client, provider)


# ---------------------------------------------------------------------------
# Google Generative AI wrapper
# ---------------------------------------------------------------------------

class _TrackedGoogleModel:
    def __init__(self, client, provider: str):
        self._client = client
        self._provider = provider

    def generate_content(self, *args, **kwargs):
        response = self._client.generate_content(*args, **kwargs)
        # Google's model name is on the client object
        model = getattr(self._client, "model_name", None) or "unknown"
        usage = getattr(response, "usage_metadata", None)
        _record(
            model=model,
            provider=self._provider,
            input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
            output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
        )
        return response

    def __getattr__(self, name):
        return getattr(self._client, name)


def _wrap_google(client, provider: str):
    return _TrackedGoogleModel(client, provider)
