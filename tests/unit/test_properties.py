"""Unit tests for task_to_notion_properties."""
from __future__ import annotations

from src.notion_processor import ExtractedTask, task_to_notion_properties


def test_all_core_fields_present() -> None:
    task = ExtractedTask(
        task_name="Reply to Sarah",
        context="Send revised contract.",
        eisenhower="Q3 Delegate",
        schedule_date="2026-05-23T08:00:00-07:00",
    )
    props = task_to_notion_properties(task)
    assert props["Task Name"]["title"][0]["text"]["content"] == "Reply to Sarah"
    assert props["Context"]["rich_text"][0]["text"]["content"] == "Send revised contract."
    assert props["Status"]["status"]["name"] == "Draft"
    assert props["Eisenhower"]["select"]["name"] == "Q3 Delegate"
    assert props["Schedule Date"]["date"]["start"] == "2026-05-23T08:00:00-07:00"
    assert "Target" not in props
    assert "Risk Tier" not in props
    assert "Time Budget" not in props
    assert "Reflection" not in props


def test_q2_blank_schedule_date_omitted() -> None:
    task = ExtractedTask(
        task_name="File quarterly taxes",
        context="Block time before Jan 15 deadline.",
        eisenhower="Q2 Schedule",
        schedule_date="",
    )
    props = task_to_notion_properties(task)
    assert "Schedule Date" not in props
