"""Unit tests for blocks_to_text."""
from __future__ import annotations

import json

from src.notion_client import blocks_to_text


def test_briefing_blocks_fixture(fixtures_dir) -> None:
    blocks = json.loads(
        (fixtures_dir / "notion_blocks" / "briefing_blocks.json").read_text()
    )
    text = blocks_to_text(blocks)
    assert "## News" in text
    assert "HN front page headline." in text
    assert "## Inbox" in text
    assert "- Email from Sarah" in text
    assert "- [ ] Review contract" in text
    assert "---" in text


def test_unknown_block_type_skipped() -> None:
    blocks = [
        {
            "type": "unsupported_widget",
            "unsupported_widget": {"rich_text": []},
        },
        {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "plain_text": "visible", "text": {"content": "visible"}}
                ]
            },
        },
    ]
    text = blocks_to_text(blocks)
    assert "visible" in text
    assert "unsupported" not in text.lower()
