"""Unit tests for extract_from_page orchestration (mocked I/O)."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.notion_processor import ExtractorError, extract_from_page


HAPPY_JSON = json.dumps(
    {
        "tasks": [
            {
                "task_name": "Reply to Sarah",
                "context": "Acme contract by Monday.",
                "do": "Draft and send revised contract to Sarah Chen",
                "why": "She asked for it by EOD Monday.",
                "steps": [],
                "eisenhower": "Q3 Delegate",
                "schedule_date": "2026-05-23T08:00:00-07:00",
            }
        ]
    }
)


def test_empty_body_returns_zero_tasks() -> None:
    with patch("src.notion_processor.read_page_blocks", return_value=[]):
        with patch("src.notion_processor.blocks_to_text", return_value=""):
            result = extract_from_page("page-123")
    assert result.tasks_written == 0
    assert result.dry_run is False


def test_dry_run_skips_notion_write() -> None:
    blocks = [{"type": "heading_2", "heading_2": {"rich_text": []}}]
    with patch("src.notion_processor.read_page_blocks", return_value=blocks):
        with patch("src.notion_processor.blocks_to_text", return_value="Inbox content"):
            with patch("src.notion_processor.call_llm", return_value=HAPPY_JSON):
                with patch("src.notion_processor.create_task_draft") as mock_write:
                    result = extract_from_page("page-123", dry_run=True)
    mock_write.assert_not_called()
    assert result.tasks_written == 0
    assert result.dry_run is True


def test_live_run_writes_tasks() -> None:
    blocks = [{"type": "heading_2", "heading_2": {"rich_text": []}}]
    with patch("src.notion_processor.read_page_blocks", return_value=blocks):
        with patch("src.notion_processor.blocks_to_text", return_value="Inbox content"):
            with patch("src.notion_processor.call_llm", return_value=HAPPY_JSON):
                with patch(
                    "src.notion_processor.create_task_draft", return_value="task-page-id"
                ) as mock_write:
                    result = extract_from_page("page-123", dry_run=False)
    mock_write.assert_called_once()
    assert result.tasks_written == 1
    assert result.task_page_ids == ["task-page-id"]


def test_live_run_passes_children_blocks() -> None:
    """create_task_draft must be called with a non-empty children= kwarg."""
    blocks = [{"type": "heading_2", "heading_2": {"rich_text": []}}]
    with patch("src.notion_processor.read_page_blocks", return_value=blocks):
        with patch("src.notion_processor.blocks_to_text", return_value="Inbox content"):
            with patch("src.notion_processor.call_llm", return_value=HAPPY_JSON):
                with patch(
                    "src.notion_processor.create_task_draft", return_value="task-page-id"
                ) as mock_write:
                    extract_from_page("page-123", dry_run=False)
    call_kwargs = mock_write.call_args.kwargs
    assert "children" in call_kwargs
    assert isinstance(call_kwargs["children"], list)
    assert len(call_kwargs["children"]) > 0
    block_types = [b["type"] for b in call_kwargs["children"]]
    assert "heading_2" in block_types
    assert "paragraph" in block_types


def test_llm_parse_error_propagates() -> None:
    blocks = [{"type": "heading_2", "heading_2": {"rich_text": []}}]
    with patch("src.notion_processor.read_page_blocks", return_value=blocks):
        with patch("src.notion_processor.blocks_to_text", return_value="body"):
            with patch("src.notion_processor.call_llm", return_value="not json"):
                with pytest.raises(ExtractorError):
                    extract_from_page("page-123")
