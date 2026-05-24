"""Checkpoint 3: Full extractor round-trip in dry-run mode.

Reads the page, calls the LLM, parses the response, applies Eisenhower
defaults, and prints the would-be Tasks. Writes nothing to Notion.

Usage:
    python tests/manual/03_extractor_dry_run.py <briefing_page_id>

Pass criteria: the script completes without raising and prints a (possibly
empty) Task list. The QUALITY of the extraction is up to you to judge —
this is the iteration loop for tuning prompts/notion_processor_extract.md.
"""
from __future__ import annotations

import sys

import _bootstrap  # noqa: F401

from src.notion_processor import extract_from_page


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python tests/manual/03_extractor_dry_run.py <page_id>")
        return 2
    page_id = sys.argv[1].strip()
    if not page_id:
        print("FAIL: empty page_id")
        return 1

    try:
        result = extract_from_page(page_id, dry_run=True)
    except Exception as exc:
        print(f"FAIL: extract_from_page raised {type(exc).__name__}: {exc}")
        return 1

    print()
    print(f"PASS: dry run complete — {result.tasks_written} would-be Tasks "
          "(see above for details)")
    print("  → tune prompts/notion_processor_extract.md, re-run this script")
    print("  → when you're happy with output, move on to checkpoint 04")
    return 0


if __name__ == "__main__":
    sys.exit(main())
