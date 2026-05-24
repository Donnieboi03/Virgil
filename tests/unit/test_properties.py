"""Unit tests for task_to_notion_properties."""
from __future__ import annotations

from src.notion_processor import ExtractedTask, task_to_notion_properties


def test_all_core_fields_present() -> None:
    task = ExtractedTask(
        task_name="Reply to Sarah",
        context="Send revised contract.",
        target="Gmail",
        risk_tier="1-Draft",
        eisenhower="Q1 Urgent+Important",
        schedule_date="2026-05-23T08:00:00-07:00",
        time_budget_seconds=None,
    )
    props = task_to_notion_properties(task)
    assert props["Task Name"]["title"][0]["text"]["content"] == "Reply to Sarah"
    assert props["Target"]["select"]["name"] == "Gmail"
    assert props["Risk Tier"]["select"]["name"] == "1-Draft"
    assert props["Status"]["status"]["name"] == "Draft"
    assert props["Eisenhower"]["select"]["name"] == "Q1 Urgent+Important"
    assert props["Schedule Date"]["date"]["start"] == "2026-05-23T08:00:00-07:00"
    assert "Time Budget" not in props


def test_time_budget_included_when_set() -> None:
    task = ExtractedTask(
        task_name="Research",
        context="Long session.",
        target="Browser",
        risk_tier="2-Approval",
        eisenhower="Q2 Important",
        schedule_date="2026-05-25T09:00:00-07:00",
        time_budget_seconds=1800,
    )
    props = task_to_notion_properties(task)
    assert props["Time Budget"]["number"] == 1800
