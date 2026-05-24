"""Integration: LLM provider reachable (OpenRouter or Gemini)."""
from __future__ import annotations

import pytest

from src import llm

pytestmark = pytest.mark.integration


def test_llm_hello() -> None:
    provider = llm.resolve_provider()
    content = llm.complete(
        "You are a connectivity test.",
        "Reply with exactly the word: pong",
        json_mode=False,
        temperature=0.0,
    )
    assert content.strip()
