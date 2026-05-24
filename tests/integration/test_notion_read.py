"""Integration: read a real Daily Briefing page from Notion."""
from __future__ import annotations

import os

import pytest

from src.notion_client import blocks_to_text, read_page_blocks

pytestmark = pytest.mark.integration


@pytest.fixture
def briefing_page_id() -> str:
    page_id = os.environ.get("TEST_BRIEFING_PAGE_ID", "").strip()
    if not page_id:
        pytest.skip("TEST_BRIEFING_PAGE_ID not set in environment")
    return page_id


def test_read_briefing_page(briefing_page_id: str) -> None:
    blocks = read_page_blocks(briefing_page_id)
    assert blocks
    text = blocks_to_text(blocks)
    assert text.strip()
    markers = ["News", "Inbox", "Schedule"]
    assert any(m.lower() in text.lower() for m in markers)
