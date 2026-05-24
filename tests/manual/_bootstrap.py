"""Ensure repo root is on sys.path when manual scripts are run directly.

Run from the project root:
    python tests/manual/03_extractor_dry_run.py <page_id>
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_root_str = str(_ROOT)
if _root_str not in sys.path:
    sys.path.insert(0, _root_str)
