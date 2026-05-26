"""Manual checkpoint: token/cost report for one live LLM extraction.

Calls the extractor with complete_with_usage() so we capture actual prompt+
completion tokens, then looks up cost via scripts/llm_pricing.py.

Usage:
    python tests/manual/08_cost_report.py <briefing_page_id>

Output example:
    Model:              gemini-2.5-flash
    Provider:           gemini
    Source page:        abc123...  (~47 blocks, 3812 chars body)
    Prompt tokens:      2541
    Completion tokens:  312
    Total tokens:       2853
    Cost this run:      $0.000571
    Projected monthly:  $0.017  (1 run/day × 30)
    Tasks emitted:      3
    Skipped notes:      "Skipped 4 items: Kraken bonus (promotional), ..."
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import _bootstrap  # noqa: F401  # sets up sys.path

# Add repo root to path so scripts/ module is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.llm_pricing import PRICING, cost_usd
from src import llm as llm_module
from src.notion_client import blocks_to_text, read_page_blocks
from src.notion_processor import (
    _build_user_message,
    _infer_source_kind,
    _load_system_prompt,
    apply_eisenhower_defaults,
    parse_extractor_output,
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python tests/manual/08_cost_report.py <page_id>")
        return 2

    page_id = sys.argv[1].strip()
    if not page_id:
        print("FAIL: empty page_id")
        return 1

    # ── Fetch page ──────────────────────────────────────────────────────────
    print(f"\n[cost-report] Fetching page {page_id} …")
    blocks = read_page_blocks(page_id)
    body_text = blocks_to_text(blocks)
    source_kind = _infer_source_kind(blocks)
    char_count = len(body_text)
    block_count = len(blocks)

    if not body_text.strip():
        print("[cost-report] Page body is empty — nothing to extract.")
        return 0

    # ── LLM call with usage ─────────────────────────────────────────────────
    now = dt.datetime.now(dt.timezone.utc).astimezone()
    system_prompt = _load_system_prompt()
    user_message = _build_user_message(body_text, now.isoformat(), source_kind)

    print("[cost-report] Calling LLM with complete_with_usage() …")
    text, usage = llm_module.complete_with_usage(
        system_prompt, user_message, json_mode=True, temperature=0.2
    )

    # ── Parse output ────────────────────────────────────────────────────────
    tasks_raw, notes = parse_extractor_output(text)
    tasks = [apply_eisenhower_defaults(t, now) for t in tasks_raw]

    # ── Cost lookup ─────────────────────────────────────────────────────────
    model = usage.model
    try:
        run_cost = cost_usd(model, usage.prompt_tokens, usage.completion_tokens)
        monthly = run_cost * 30
        cost_line = f"${run_cost:.6f}"
        monthly_line = f"${monthly:.4f}  (1 run/day × 30)"
    except KeyError as exc:
        cost_line = f"unknown — {exc}"
        monthly_line = "unknown"

    # ── Print report ────────────────────────────────────────────────────────
    width = 24
    print()
    print("=" * 52)
    print(f"{'Model:':<{width}}{model}")
    print(f"{'Provider:':<{width}}{usage.provider}")
    print(f"{'Source page:':<{width}}{page_id[:16]}…  (~{block_count} blocks, {char_count} chars body)")
    print(f"{'Prompt tokens:':<{width}}{usage.prompt_tokens:,}")
    print(f"{'Completion tokens:':<{width}}{usage.completion_tokens:,}")
    print(f"{'Total tokens:':<{width}}{usage.total_tokens:,}")
    print(f"{'Cost this run:':<{width}}{cost_line}")
    print(f"{'Projected monthly:':<{width}}{monthly_line}")
    print(f"{'Tasks emitted:':<{width}}{len(tasks)}")
    skipped = f'"{notes}"' if notes else "(none)"
    print(f"{'Skipped notes:':<{width}}{skipped}")
    print("=" * 52)

    if model not in PRICING:
        print(f"\n[cost-report] NOTE: Add '{model}' to scripts/llm_pricing.py for future cost tracking.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
