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
    _heading,
    _paragraph,
    _todo,
    blocks_to_text,
    create_task_draft,
    read_page_blocks,
)

PROMPT_PATH = ROOT / "prompts" / "notion_processor_extract.md"

VALID_EISENHOWER = {
    "Q1 Do",
    "Q2 Schedule",
    "Q3 Delegate",
}
DEFAULT_EISENHOWER = "Q3 Delegate"


@dataclass
class ExtractedTask:
    task_name: str
    context: str       # short one-liner for the Tasks board row
    eisenhower: str
    schedule_date: str  # ISO 8601 datetime string; may be blank for Q2
    do: str = ""        # closure-ready imperative for task page body
    why: str = ""       # optional single sentence
    steps: list[str] = field(default_factory=list)  # to_do checkboxes; only when source states procedure


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
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _normalize_eisenhower(raw: Any) -> str:
    """Return a valid Eisenhower value; default to Q3 Delegate when missing."""
    if not isinstance(raw, str) or not raw.strip():
        return DEFAULT_EISENHOWER
    value = raw.strip()
    if value not in VALID_EISENHOWER:
        raise ExtractorError(
            f"Invalid `eisenhower` {value!r}; "
            f"must be one of {sorted(VALID_EISENHOWER)}"
        )
    return value


def parse_extractor_output(raw: str) -> tuple[list[ExtractedTask], str | None]:
    """Turn the LLM's raw response into Task objects + an optional notes string.

    Tolerates:
      - Markdown code fences around the JSON
      - Missing `notes` field (returns None)
      - Missing `eisenhower` (defaults to Q3 Delegate)
      - Missing or blank `schedule_date` (filled by apply_eisenhower_defaults)

    Raises ExtractorError on:
      - Invalid JSON
      - Missing required Task fields
      - Invalid Eisenhower enum values
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
    required_fields = {"task_name", "context"}
    for idx, item in enumerate(tasks_raw):
        if not isinstance(item, dict):
            raise ExtractorError(f"Task at index {idx} is not an object: {item!r}")
        missing = required_fields - item.keys()
        if missing:
            raise ExtractorError(
                f"Task at index {idx} missing required fields: {sorted(missing)}"
            )

        eisenhower = _normalize_eisenhower(item.get("eisenhower"))
        schedule_raw = item.get("schedule_date", "")
        schedule_date = str(schedule_raw).strip() if schedule_raw is not None else ""

        do = str(item.get("do", "") or "").strip()
        why = str(item.get("why", "") or "").strip()
        steps_raw = item.get("steps") or []
        steps = [str(s).strip() for s in steps_raw if isinstance(s, str) and str(s).strip()]

        tasks.append(
            ExtractedTask(
                task_name=str(item["task_name"]).strip(),
                context=str(item["context"]).strip(),
                eisenhower=eisenhower,
                schedule_date=schedule_date,
                do=do,
                why=why,
                steps=steps,
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

    Q1 Do / Q3 Delegate = now. Q2 Schedule = leave blank (user sets when ready).
    If schedule_date is already a valid ISO datetime, leave it alone.
    """
    existing = (task.schedule_date or "").strip()
    if existing:
        try:
            dt.datetime.fromisoformat(existing)
            return task
        except ValueError:
            pass

    if task.eisenhower == "Q2 Schedule":
        return ExtractedTask(
            task_name=task.task_name,
            context=task.context,
            eisenhower=task.eisenhower,
            schedule_date="",
            do=task.do,
            why=task.why,
            steps=task.steps,
        )

    return ExtractedTask(
        task_name=task.task_name,
        context=task.context,
        eisenhower=task.eisenhower,
        schedule_date=now.isoformat(),
        do=task.do,
        why=task.why,
        steps=task.steps,
    )


# ─── Notion property mapping ─────────────────────────────────────────────────


def _rt(text: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": text[:2000]}}]


def task_to_notion_properties(task: ExtractedTask) -> dict[str, Any]:
    """Build the Notion property dict for a new Draft Task row.

    Writes MVP schema fields only. Reflection is left empty at extraction;
    Hermes links it after execution.
    """
    properties: dict[str, Any] = {
        "Task Name": {"title": _rt(task.task_name)},
        "Context": {"rich_text": _rt(task.context)},
        "Status": {"status": {"name": "Draft"}},
        "Eisenhower": {"select": {"name": task.eisenhower}},
    }
    if task.schedule_date.strip():
        properties["Schedule Date"] = {"date": {"start": task.schedule_date}}
    return properties


def task_to_page_blocks(task: ExtractedTask) -> list[dict[str, Any]]:
    """Build the Notion page-body blocks for a task (Do / Why / Steps).

    These blocks are written as page children at create time so the human
    can open the task and see exactly how to close it — per the closure
    principle in PLAN.md "Design principle: closure over collection".

    Only emits sections that have content:
      - "Do" heading + paragraph always (falls back to task_name if do is blank).
      - "Why" heading + paragraph only when why is non-empty.
      - "Steps" heading + to_do blocks only when steps list is non-empty.
    """
    do_text = task.do or task.task_name
    blocks: list[dict[str, Any]] = [
        _heading("Do", 2),
        _paragraph(do_text),
    ]
    if task.why:
        blocks.append(_heading("Why", 2))
        blocks.append(_paragraph(task.why))
    if task.steps:
        blocks.append(_heading("Steps", 2))
        for step in task.steps:
            blocks.append(_todo(step))
    return blocks


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
    """Cheap heuristic: peek at the page title-ish first heading."""
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
    """Top-level: read page → extract → default → write."""
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
            print(f"       eis={t.eisenhower} schedule={t.schedule_date or '(blank)'}")
            print(f"       context: {t.context}")
            print(f"       do:      {t.do or '(same as task_name)'}")
            if t.why:
                print(f"       why:     {t.why}")
            for j, step in enumerate(t.steps, 1):
                print(f"       step {j}:  {step}")
        return ProcessorResult(
            page_id=page_id,
            tasks_written=0,
            skipped_notes=notes,
            dry_run=True,
        )

    written_ids: list[str] = []
    for t in tasks:
        properties = task_to_notion_properties(t)
        body_blocks = task_to_page_blocks(t)
        task_page_id = create_task_draft(properties, children=body_blocks)
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
