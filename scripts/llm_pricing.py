"""LLM pricing table — cost_usd(model, prompt_tokens, completion_tokens) -> float.

Rates are per-million-token (input / output) in USD.
Source: provider pricing pages as of May 2026.
Verify at provider dashboard before using for billing decisions.

Add a new entry any time you see a KeyError from cost_usd().
"""
from __future__ import annotations

# fmt: off
# (model_id_as_used_in_config): (input_per_1M_usd, output_per_1M_usd)
PRICING: dict[str, tuple[float, float]] = {
    # Google Gemini (via Google AI Studio / direct API)
    "gemini-2.5-flash":              (0.15, 0.60),
    "gemini-2.0-flash":              (0.10, 0.40),
    "gemini-1.5-flash":              (0.075, 0.30),
    "gemini-1.5-pro":                (1.25, 5.00),

    # OpenRouter pass-through keys (model ids as sent to OpenRouter)
    "google/gemini-2.5-flash":       (0.15, 0.60),
    "google/gemini-2.0-flash":       (0.10, 0.40),
    "google/gemini-flash-1.5":       (0.075, 0.30),
    "anthropic/claude-sonnet-4-5":   (3.00, 15.00),
    "anthropic/claude-3-5-haiku":    (0.80, 4.00),
    "openai/gpt-4o-mini":            (0.15, 0.60),
    "openai/gpt-4o":                 (2.50, 10.00),
    "meta-llama/llama-3.1-8b-instruct": (0.06, 0.06),
}
# fmt: on


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Return estimated USD cost for one LLM call.

    Raises KeyError with a helpful message if the model is unknown — add it to
    PRICING above so future runs are tracked correctly.
    """
    if model not in PRICING:
        known = ", ".join(sorted(PRICING))
        raise KeyError(
            f"Unknown model {model!r}. Add it to scripts/llm_pricing.py PRICING dict.\n"
            f"Known models: {known}"
        )
    input_rate, output_rate = PRICING[model]
    return (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000
