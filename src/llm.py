"""LLM provider abstraction — OpenRouter or Google AI Studio (Gemini).

Selection (see resolve_provider):
  1. LLM_PROVIDER=openrouter|gemini if set (fails fast if key missing)
  2. Else OPENROUTER_API_KEY → OpenRouter
  3. Else GOOGLE_API_KEY → Gemini
  4. Else EnvironmentError

Used by notion_processor.py today; Hermes (Phase 2) should call complete() too.
"""
from __future__ import annotations

from typing import Literal

from .config import get as get_config

ProviderName = Literal["openrouter", "gemini"]


def resolve_provider() -> ProviderName:
    """Pick which LLM backend to use for this process."""
    cfg = get_config()
    forced = cfg.llm_provider.lower()
    if forced == "openrouter":
        if not cfg.openrouter_api_key:
            raise EnvironmentError(
                "LLM_PROVIDER=openrouter but OPENROUTER_API_KEY is empty. "
                "Add a key from openrouter.ai or set LLM_PROVIDER=gemini with GOOGLE_API_KEY."
            )
        return "openrouter"
    if forced == "gemini":
        if not cfg.google_api_key:
            raise EnvironmentError(
                "LLM_PROVIDER=gemini but GOOGLE_API_KEY is empty. "
                "Add a key from aistudio.google.com or set OPENROUTER_API_KEY."
            )
        return "gemini"
    if forced:
        raise EnvironmentError(
            f"Unknown LLM_PROVIDER={cfg.llm_provider!r}. Use 'openrouter' or 'gemini'."
        )

    if cfg.openrouter_api_key:
        return "openrouter"
    if cfg.google_api_key:
        return "gemini"

    raise EnvironmentError(
        "No LLM configured. Set OPENROUTER_API_KEY (openrouter.ai) or "
        "GOOGLE_API_KEY (aistudio.google.com) in .env."
    )


def _model_name(provider: ProviderName) -> str:
    cfg = get_config()
    if provider == "openrouter":
        return cfg.llm_model
    return cfg.gemini_model


def _call_openrouter(
    system: str, user: str, *, json_mode: bool, temperature: float
) -> str:
    from openai import OpenAI

    cfg = get_config()
    client = OpenAI(
        api_key=cfg.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    kwargs: dict = {
        "model": cfg.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return (response.choices[0].message.content or "").strip()


def _call_gemini(
    system: str, user: str, *, json_mode: bool, temperature: float
) -> str:
    from google import genai
    from google.genai import types

    cfg = get_config()
    client = genai.Client(api_key=cfg.google_api_key)
    config_kwargs: dict = {"temperature": temperature}
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"

    response = client.models.generate_content(
        model=cfg.gemini_model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            **config_kwargs,
        ),
    )
    text = (response.text or "").strip()
    return text


def complete(
    system: str,
    user: str,
    *,
    json_mode: bool = True,
    temperature: float = 0.2,
) -> str:
    """Send a chat completion to the resolved provider; return assistant text."""
    provider = resolve_provider()
    model = _model_name(provider)
    print(f"[llm] provider={provider} model={model} json_mode={json_mode}")

    if provider == "openrouter":
        content = _call_openrouter(
            system, user, json_mode=json_mode, temperature=temperature
        )
    else:
        content = _call_gemini(
            system, user, json_mode=json_mode, temperature=temperature
        )

    if not content:
        raise RuntimeError(f"LLM ({provider}) returned an empty message.")
    return content
