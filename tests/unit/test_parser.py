"""Unit tests for parse_extractor_output."""
from __future__ import annotations

import json

import pytest

from src.notion_processor import ExtractorError, parse_extractor_output


class TestHappyPath:
    def test_single_task(self) -> None:
        raw = json.dumps(
            {
                "tasks": [
                    {
                        "task_name": "Reply to Sarah",
                        "context": "Acme contract revision needed by Mon EOD.",
                        "target": "Gmail",
                        "risk_tier": "1-Draft",
                        "eisenhower": "Q1 Urgent+Important",
                        "schedule_date": "2026-05-23T08:00:00-07:00",
                    }
                ]
            }
        )
        tasks, notes = parse_extractor_output(raw)
        assert len(tasks) == 1
        assert notes is None
        assert tasks[0].task_name == "Reply to Sarah"

    def test_fenced_json_from_fixture(self, fixtures_dir) -> None:
        raw = (fixtures_dir / "llm_responses" / "malformed_fenced.json").read_text()
        tasks, notes = parse_extractor_output(raw)
        assert len(tasks) == 1
        assert tasks[0].target == "Manual"

    def test_happy_path_fixture(self, fixtures_dir) -> None:
        raw = (fixtures_dir / "llm_responses" / "happy_path.json").read_text()
        tasks, notes = parse_extractor_output(raw)
        assert len(tasks) == 1
        assert notes is not None
        assert "Q4" in notes


class TestQ4SkipRule:
    def test_q4_task_dropped(self) -> None:
        raw = json.dumps(
            {
                "tasks": [
                    {
                        "task_name": "Read HN thread on Rust",
                        "context": "Informational only",
                        "target": "Browser",
                        "risk_tier": "2-Approval",
                        "eisenhower": "Q4 Neither",
                        "schedule_date": "2026-05-23T08:00:00-07:00",
                    }
                ]
            }
        )
        tasks, _ = parse_extractor_output(raw)
        assert len(tasks) == 0

    def test_q4_skip_notes_fixture(self, fixtures_dir) -> None:
        raw = (fixtures_dir / "llm_responses" / "q4_skip.json").read_text()
        tasks, notes = parse_extractor_output(raw)
        assert len(tasks) == 0
        assert notes is not None


class TestTimeBudget:
    def test_time_budget_present(self) -> None:
        raw = json.dumps(
            {
                "tasks": [
                    {
                        "task_name": "Long research session",
                        "context": "Compare 5 vendor SLAs.",
                        "target": "Browser",
                        "risk_tier": "2-Approval",
                        "eisenhower": "Q2 Important",
                        "schedule_date": "2026-05-25T09:00:00-07:00",
                        "time_budget_seconds": 1800,
                    }
                ]
            }
        )
        tasks, _ = parse_extractor_output(raw)
        assert tasks[0].time_budget_seconds == 1800

    def test_time_budget_null(self) -> None:
        raw = json.dumps(
            {
                "tasks": [
                    {
                        "task_name": "Quick check",
                        "context": "Verify something.",
                        "target": "Manual",
                        "risk_tier": "3-Manual",
                        "eisenhower": "Q2 Important",
                        "schedule_date": "2026-05-25T09:00:00-07:00",
                        "time_budget_seconds": None,
                    }
                ]
            }
        )
        tasks, _ = parse_extractor_output(raw)
        assert tasks[0].time_budget_seconds is None


class TestMalformedInput:
    @pytest.mark.parametrize(
        "raw,fragment",
        [
            ("this is not json at all", "not valid JSON"),
            ("[1, 2, 3]", "Expected JSON object"),
            (
                '{"tasks":[{"task_name":"x","target":"Gmail","risk_tier":"1-Draft",'
                '"eisenhower":"Q1 Urgent+Important","schedule_date":"2026-05-23T08:00:00-07:00"}]}',
                "missing required fields",
            ),
            (
                '{"tasks":[{"task_name":"x","context":"y","target":"Telegram",'
                '"risk_tier":"1-Draft","eisenhower":"Q1 Urgent+Important",'
                '"schedule_date":"2026-05-23T08:00:00-07:00"}]}',
                "invalid `target`",
            ),
            (
                '{"tasks":[{"task_name":"x","context":"y","target":"Gmail",'
                '"risk_tier":"5-WildWest","eisenhower":"Q1 Urgent+Important",'
                '"schedule_date":"2026-05-23T08:00:00-07:00"}]}',
                "invalid `risk_tier`",
            ),
        ],
    )
    def test_raises_extractor_error(self, raw: str, fragment: str) -> None:
        with pytest.raises(ExtractorError, match=fragment):
            parse_extractor_output(raw)
