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
        eisenhower="Q1 Do",
        schedule_date="",
    )
    base.update(overrides)
    return ExtractedTask(**base)


def test_q1_defaults_to_now() -> None:
    result = apply_eisenhower_defaults(_task(eisenhower="Q1 Do"), NOW)
    assert result.schedule_date == NOW.isoformat()


def test_q3_defaults_to_now() -> None:
    result = apply_eisenhower_defaults(_task(eisenhower="Q3 Delegate"), NOW)
    assert result.schedule_date == NOW.isoformat()


def test_q2_leaves_schedule_blank() -> None:
    result = apply_eisenhower_defaults(_task(eisenhower="Q2 Schedule"), NOW)
    assert result.schedule_date == ""


def test_existing_valid_schedule_date_preserved() -> None:
    existing = "2026-06-01T10:00:00-07:00"
    result = apply_eisenhower_defaults(
        _task(schedule_date=existing, eisenhower="Q2 Schedule"), NOW
    )
    assert result.schedule_date == existing


def test_invalid_schedule_date_q2_stays_blank() -> None:
    result = apply_eisenhower_defaults(
        _task(schedule_date="not-a-date", eisenhower="Q2 Schedule"), NOW
    )
    assert result.schedule_date == ""


def test_invalid_schedule_date_q3_replaced_with_now() -> None:
    result = apply_eisenhower_defaults(
        _task(schedule_date="not-a-date", eisenhower="Q3 Delegate"), NOW
    )
    assert result.schedule_date == NOW.isoformat()
