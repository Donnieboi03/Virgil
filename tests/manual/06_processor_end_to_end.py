"""Checkpoint 6: full processor against a real briefing, writes real Drafts.

This is the first checkpoint that costs real money (~$0.002) AND writes
real rows to Notion. Run after 03 dry-run looks good.

Usage:
    python tests/manual/06_processor_end_to_end.py <briefing_page_id>

Pass criteria: the script reports N tasks written, and opening the Tasks
DB in Notion shows N new Draft rows whose fields look reasonable.

Cleanup: review the new Drafts in Notion. Approve the good ones, delete
the bad ones. The next iteration of your prompt should reduce false
positives.
"""
from __future__ import annotations

import sys

import _bootstrap  # noqa: F401

from src.notion_processor import extract_from_page


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python tests/manual/06_processor_end_to_end.py <page_id>")
        return 2
    page_id = sys.argv[1].strip()
    if not page_id:
        print("FAIL: empty page_id")
        return 1

    print("WARNING: this will write real Drafts to your Tasks DB.")
    print("If 03 dry-run isn't producing acceptable output yet, stop now and tune the prompt first.")
    print()
    try:
        result = extract_from_page(page_id, dry_run=False)
    except Exception as exc:
        print(f"FAIL: extract_from_page raised {type(exc).__name__}: {exc}")
        if "PARTIAL" not in str(exc):
            print("  → may have written some Drafts before failing; check Tasks DB")
        return 1

    print()
    print(f"PASS: end-to-end run wrote {result.tasks_written} Draft Task(s)")
    if result.skipped_notes:
        print(f"  notes: {result.skipped_notes}")
    print("  → open Tasks DB, sanity-check the new Drafts")
    print("  → when satisfied, move on to checkpoint 07 (chained ingestion)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
