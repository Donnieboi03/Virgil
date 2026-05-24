"""Daily Briefing → Draft Tasks bridge (Phase 1.5).

Reads a Notion page body (Daily Briefing, Meeting Notes, or Opportunity),
asks an LLM via src/llm.py (OpenRouter or Gemini) to extract action items as
structured JSON, and writes one Draft row per item into the Tasks DB.

This module is the ONLY writer of new Task rows in the Virgil architecture.
Hermes (Phase 2) never creates Tasks — it only reads Tasks with
Status=Approved and updates status/log/reflection fields.

CLI usage:
    python -m src.notion_processor --page-id <notion_page_id>
    python -m src.notion_processor --page-id <notion_page_id> --dry-run

The chained invocation pattern is the default: src/ingestion.py calls
extract_from_page() at the end of its run with the freshly-created
briefing page id. See ingestion.py for the call site.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .config import ROOT, get as get_config
from . import llm
from .notion_client import (
    blocks_to_text,
    create_task_draft,
    read_page_blocks,
)

PROMPT_PATH = ROOT / "prompts" / "notion_processor_extract.md"

VALID_TARGETS = {"Gmail", "Calendar", "Notion", "Browser", "Manual"}
VALID_RISK_TIERS = {"0-Auto", "1-Draft", "2-Approval", "3-Manual"}
VALID_EISENHOWER = {
    "Q1 Urgent+Important",
    "Q2 Important",
    "Q3 Urgent",
    "Q4 Neither",
}

DEFAULT_TIME_BUDGET_SECONDS = 120


@dataclass
class ExtractedTask:
    task_name: str
    context: str
    target: str
    risk_tier: str
    eisenhower: str
    schedule_date: str  # ISO 8601 datetime string
    time_budget_seconds: int | None = None


@dataclass
class ProcessorResult:
    page_id: str
    tasks_written: int
    task_page_ids: list[str] = field(default_factory=list)
    skipped_notes: str | None = None
    dry_run: bool = False


class ExtractorError(RuntimeError):
    """Raised when the LLM output cannot be parsed into Tasks."""


# ─── Prompt loading ──────────────────────────────────────────────────────────


def _load_system_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Extraction prompt not found at {PROMPT_PATH}. "
            "It is part of the repo; reinstall or check your working tree."
        )
    return PROMPT_PATH.read_text(encoding="utf-8")


# ─── Parsing ─────────────────────────────────────────────────────────────────


def _strip_code_fence(raw: str) -> str:
    """If the model wrapped its JSON in markdown fences, peel them off."""
    text = raw.strip()
    if text.startswith("```"):
        # Drop opening fence (with optional language tag).
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        # Drop trailing fence.
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def parse_extractor_output(raw: str) -> tuple[list[ExtractedTask], str | None]:
    """Turn the LLM's raw response into Task objects + an optional notes string.

    Tolerates:
      - Markdown code fences around the JSON
      - Missing `notes` field (returns None)
      - `time_budget_seconds` missing or null (returns None on the Task)

    Raises ExtractorError on:
      - Invalid JSON
      - Missing required Task fields
      - Enum values not in the allowed sets
    """
    cleaned = _strip_code_fence(raw)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ExtractorError(f"LLM output was not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ExtractorError(
            f"Expected JSON object, got {type(payload).__name__}: {payload!r}"
        )

    tasks_raw = payload.get("tasks", [])
    if not isinstance(tasks_raw, list):
        raise ExtractorError(
            f"`tasks` must be a list, got {type(tasks_raw).__name__}"
        )

    tasks: list[ExtractedTask] = []
    required_fields = {
        "task_name",
        "context",
        "target",
        "risk_tier",
        "eisenhower",
        "schedule_date",
    }
    for idx, item in enumerate(tasks_raw):
        if not isinstance(item, dict):
            raise ExtractorError(f"Task at index {idx} is not an object: {item!r}")
        missing = required_fields - item.keys()
        if missing:
            raise ExtractorError(
                f"Task at index {idx} missing required fields: {sorted(missing)}"
            )

        target = item["target"]
        if target not in VALID_TARGETS:
            raise ExtractorError(
                f"Task {idx} has invalid `target` {target!r}; "
                f"must be one of {sorted(VALID_TARGETS)}"
            )

        risk_tier = item["risk_tier"]
        if risk_tier not in VALID_RISK_TIERS:
            raise ExtractorError(
                f"Task {idx} has invalid `risk_tier` {risk_tier!r}; "
                f"must be one of {sorted(VALID_RISK_TIERS)}"
            )

        eisenhower = item["eisenhower"]
        if eisenhower not in VALID_EISENHOWER:
            raise ExtractorError(
                f"Task {idx} has invalid `eisenhower` {eisenhower!r}; "
                f"must be one of {sorted(VALID_EISENHOWER)}"
            )

        if eisenhower == "Q4 Neither":
            # Defense in depth: the prompt tells the model to SKIP Q4 entirely.
            # If a Q4 leaks through anyway, treat it as a notes addition rather
            # than letting it pollute the Tasks DB.
            continue

        time_budget = item.get("time_budget_seconds")
        if time_budget is not None and not isinstance(time_budget, int):
            try:
                time_budget = int(time_budget)
            except (TypeError, ValueError) as exc:
                raise ExtractorError(
                    f"Task {idx} has non-integer `time_budget_seconds` "
                    f"{time_budget!r}"
                ) from exc

        tasks.append(
            ExtractedTask(
                task_name=str(item["task_name"]).strip(),
                context=str(item["context"]).strip(),
                target=target,
                risk_tier=risk_tier,
                eisenhower=eisenhower,
                schedule_date=str(item["schedule_date"]).strip(),
                time_budget_seconds=time_budget,
            )
        )

    notes_raw = payload.get("notes")
    notes: str | None = None
    if isinstance(notes_raw, str) and notes_raw.strip():
        notes = notes_raw.strip()

    return tasks, notes


# ─── Eisenhower default schedule_date ────────────────────────────────────────


def apply_eisenhower_defaults(
    task: ExtractedTask, now: dt.datetime
) -> ExtractedTask:
    """Fill schedule_date if missing/blank per the Eisenhower → default rule.

    Q1/Q3 = now, Q2 = now + 2 days, Q4 = (already filtered out at parse time).
    If schedule_date is already a valid ISO datetime, leave it alone.
    """
    existing = (task.schedule_date or "").strip()
    if existing:
        try:
            dt.datetime.fromisoformat(existing)
            return task
        except ValueError:
            pass

    if task.eisenhower == "Q2 Important":
        default = now + dt.timedelta(days=2)
    else:
        default = now

    return ExtractedTask(
        task_name=task.task_name,
        context=task.context,
        target=task.target,
        risk_tier=task.risk_tier,
        eisenhower=task.eisenhower,
        schedule_date=default.isoformat(),
        time_budget_seconds=task.time_budget_seconds,
    )


# ─── Notion property mapping ─────────────────────────────────────────────────


def _rt(text: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": text[:2000]}}]


def task_to_notion_properties(task: ExtractedTask) -> dict[str, Any]:
    """Build the Notion property dict for a new Draft Task row.

    Schedule Date is written with a time component; Notion accepts the full
    ISO 8601 datetime string. Time Budget is omitted entirely when None so
    that Notion's default-blank behavior shows through in the UI.
    """
    properties: dict[str, Any] = {
        "Task Name": {"title": _rt(task.task_name)},
        "Context": {"rich_text": _rt(task.context)},
        "Target": {"select": {"name": task.target}},
        "Risk Tier": {"select": {"name": task.risk_tier}},
        "Status": {"status": {"name": "Draft"}},
        "Eisenhower": {"select": {"name": task.eisenhower}},
        "Schedule Date": {"date": {"start": task.schedule_date}},
    }
    if task.time_budget_seconds is not None:
        properties["Time Budget"] = {"number": task.time_budget_seconds}
    return properties


# ─── LLM call ────────────────────────────────────────────────────────────────


def _build_user_message(body_text: str, now_iso: str, source_kind: str) -> str:
    return (
        f"Current datetime: {now_iso}\n"
        f"Source kind: {source_kind}\n"
        "\n---\n\n"
        f"{body_text}"
    )


def call_llm(body_text: str, now: dt.datetime, source_kind: str) -> str:
    """Send the body to the configured LLM provider; return raw JSON text."""
    system_prompt = _load_system_prompt()
    user_message = _build_user_message(body_text, now.isoformat(), source_kind)
    try:
        return llm.complete(
            system_prompt,
            user_message,
            json_mode=True,
            temperature=0.2,
        )
    except RuntimeError as exc:
        raise ExtractorError(str(exc)) from exc


# ─── Orchestrator ────────────────────────────────────────────────────────────


def _infer_source_kind(blocks: list[dict[str, Any]]) -> str:
    """Cheap heuristic: peek at the page title-ish first heading.

    Today only Daily Briefings exist in the pipeline. Meeting Notes /
    Opportunities will land as their own ingesters in later phases. Keep this
    simple now and expand it later.
    """
    for block in blocks:
        if block.get("type") in {"heading_1", "heading_2"}:
            text = "".join(
                r.get("plain_text", "")
                for r in block.get(block["type"], {}).get("rich_text", [])
            ).lower()
            if "meeting" in text:
                return "Meeting Notes"
            if "opportunity" in text:
                return "Opportunity"
            break
    return "Daily Briefing"


def extract_from_page(
    page_id: str, *, dry_run: bool = False
) -> ProcessorResult:
    """Top-level: read page → extract → default → write.

    On dry_run=True, skips the Notion write step entirely and prints the
    Task list to stdout. Used by tests/manual/03_extractor_dry_run.py for
    prompt iteration without burning Notion writes.
    """
    cfg = get_config()
    tz = ZoneInfo(cfg.timezone)
    now = dt.datetime.now(tz)

    print(f"[processor] reading page {page_id}")
    blocks = read_page_blocks(page_id)
    body_text = blocks_to_text(blocks)
    if not body_text.strip():
        print("[processor] page body is empty; nothing to extract")
        return ProcessorResult(page_id=page_id, tasks_written=0, dry_run=dry_run)

    source_kind = _infer_source_kind(blocks)
    print(f"[processor] source kind: {source_kind}, {len(blocks)} blocks")

    provider = llm.resolve_provider()
    model = cfg.llm_model if provider == "openrouter" else cfg.gemini_model
    print(f"[processor] calling LLM ({provider}/{model})")
    raw = call_llm(body_text, now, source_kind)
    tasks, notes = parse_extractor_output(raw)
    print(f"[processor] extracted {len(tasks)} candidate tasks")
    if notes:
        print(f"[processor] notes: {notes}")

    tasks = [apply_eisenhower_defaults(t, now) for t in tasks]

    if dry_run:
        print("[processor] --dry-run: not writing to Notion")
        for i, t in enumerate(tasks, start=1):
            print(f"  [{i}] {t.task_name}")
            print(f"       target={t.target} risk={t.risk_tier} "
                  f"eis={t.eisenhower} schedule={t.schedule_date}")
            print(f"       context: {t.context}")
            if t.time_budget_seconds is not None:
                print(f"       time_budget_seconds={t.time_budget_seconds}")
        return ProcessorResult(
            page_id=page_id,
            tasks_written=0,
            skipped_notes=notes,
            dry_run=True,
        )

    written_ids: list[str] = []
    for t in tasks:
        properties = task_to_notion_properties(t)
        task_page_id = create_task_draft(properties)
        written_ids.append(task_page_id)
        print(f"[processor] wrote Draft: {t.task_name} ({task_page_id})")

    return ProcessorResult(
        page_id=page_id,
        tasks_written=len(written_ids),
        task_page_ids=written_ids,
        skipped_notes=notes,
        dry_run=False,
    )


# ─── CLI ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract Draft Tasks from a Notion page (Phase 1.5)."
    )
    parser.add_argument(
        "--page-id",
        required=True,
        help="Notion page ID of the source document (Daily Briefing, etc.)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print extracted tasks to stdout without writing to Notion.",
    )
    args = parser.parse_args()

    try:
        result = extract_from_page(args.page_id, dry_run=args.dry_run)
    except Exception as exc:
        print(f"[processor] FATAL: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        f"[processor] done — wrote {result.tasks_written} Draft Tasks"
        + (" (dry-run)" if result.dry_run else "")
    )


if __name__ == "__main__":
    main()
