"""Unit tests for apply_eisenhower_defaults."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from src.notion_processor import ExtractedTask, apply_eisenhower_defaults

TZ = ZoneInfo("America/Los_Angeles")
NOW = dt.datetime(2026, 5, 23, 8, 0, 0, tzinfo=TZ)


def _task(**overrides) -> ExtractedTask:
    base = dict(
        task_name="Test",
        context="ctx",
        target="Manual",
        risk_tier="2-Approval",
        eisenhower="Q1 Urgent+Important",
        schedule_date="",
        time_budget_seconds=None,
    )
    base.update(overrides)
    return ExtractedTask(**base)


def test_q1_defaults_to_now() -> None:
    result = apply_eisenhower_defaults(_task(eisenhower="Q1 Urgent+Important"), NOW)
    assert result.schedule_date == NOW.isoformat()


def test_q3_defaults_to_now() -> None:
    result = apply_eisenhower_defaults(_task(eisenhower="Q3 Urgent"), NOW)
    assert result.schedule_date == NOW.isoformat()


def test_q2_defaults_to_plus_two_days() -> None:
    result = apply_eisenhower_defaults(_task(eisenhower="Q2 Important"), NOW)
    expected = (NOW + dt.timedelta(days=2)).isoformat()
    assert result.schedule_date == expected


def test_existing_valid_schedule_date_preserved() -> None:
    existing = "2026-06-01T10:00:00-07:00"
    result = apply_eisenhower_defaults(
        _task(schedule_date=existing, eisenhower="Q2 Important"), NOW
    )
    assert result.schedule_date == existing


def test_invalid_schedule_date_replaced() -> None:
    result = apply_eisenhower_defaults(
        _task(schedule_date="not-a-date", eisenhower="Q2 Important"), NOW
    )
    expected = (NOW + dt.timedelta(days=2)).isoformat()
    assert result.schedule_date == expected
