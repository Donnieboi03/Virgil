"""Checkpoint 7: full chained ingestion (briefing + extraction in one run).

Runs `python -m src.ingestion` as a subprocess and reports whether both
halves of the pipeline completed. Use this to verify the launchd-triggered
morning cron will produce both a briefing AND Draft Tasks unattended.

Usage:
    python tests/manual/07_chained_ingestion.py

Pass criteria:
- Subprocess exits 0
- stdout contains both "[ingestion] briefing page" and
  "[ingestion] extracted N Draft Tasks"

This script writes real things to Notion (a fresh briefing and Draft Tasks).
It's the same effect as running launchctl start com.virgil.ingestion.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    print("running: python -m src.ingestion")
    print("(this calls real Gmail, Calendar, Notion, and OpenRouter APIs)")
    print()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "src.ingestion"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        print("FAIL: ingestion took longer than 5 minutes; check network / API health")
        return 1

    print("─── stdout ────────────────────────────────────────────────")
    print(proc.stdout)
    print("─── stderr ────────────────────────────────────────────────")
    print(proc.stderr)
    print("───────────────────────────────────────────────────────────")

    if proc.returncode != 0:
        print(f"FAIL: ingestion exited with code {proc.returncode}")
        return 1

    if "[ingestion] briefing page" not in proc.stdout:
        print("FAIL: no briefing page line in stdout — briefing step failed")
        return 1

    if "[ingestion] extracted" not in proc.stdout:
        print(
            "FAIL: no extraction line in stdout — briefing landed but "
            "extractor was skipped or failed silently"
        )
        return 1

    print()
    print("PASS: chained ingestion produced briefing AND ran extractor")
    print("  → tomorrow's 08:00 launchd run should do the same unattended")
    print("  → check logs/ingestion.log tomorrow to confirm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
