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
                        "eisenhower": "Q3 Delegate",
                        "schedule_date": "2026-05-23T08:00:00-07:00",
                    }
                ]
            }
        )
        tasks, notes = parse_extractor_output(raw)
        assert len(tasks) == 1
        assert notes is None
        assert tasks[0].task_name == "Reply to Sarah"
        assert tasks[0].eisenhower == "Q3 Delegate"

    def test_fenced_json_from_fixture(self, fixtures_dir) -> None:
        raw = (fixtures_dir / "llm_responses" / "malformed_fenced.json").read_text()
        tasks, notes = parse_extractor_output(raw)
        assert len(tasks) == 1
        assert tasks[0].eisenhower == "Q3 Delegate"

    def test_happy_path_fixture(self, fixtures_dir) -> None:
        raw = (fixtures_dir / "llm_responses" / "happy_path.json").read_text()
        tasks, notes = parse_extractor_output(raw)
        assert len(tasks) == 1
        assert notes is not None
        assert "Skipped" in notes

    def test_missing_eisenhower_defaults_to_q3(self) -> None:
        raw = json.dumps(
            {
                "tasks": [
                    {
                        "task_name": "Ack email",
                        "context": "Send a quick thanks.",
                    }
                ]
            }
        )
        tasks, _ = parse_extractor_output(raw)
        assert tasks[0].eisenhower == "Q3 Delegate"


class TestSkippedItems:
    def test_empty_tasks_with_notes(self, fixtures_dir) -> None:
        raw = (fixtures_dir / "llm_responses" / "q4_skip.json").read_text()
        tasks, notes = parse_extractor_output(raw)
        assert len(tasks) == 0
        assert notes is not None


class TestV4Fields:
    def test_do_why_steps_parsed(self) -> None:
        raw = json.dumps(
            {
                "tasks": [
                    {
                        "task_name": "Fix failed payment",
                        "context": "Lovable $25 charge failed.",
                        "do": "Log in to Lovable and update payment method",
                        "why": "Service will be suspended if payment remains outstanding.",
                        "steps": ["Open lovable.dev", "Go to billing settings", "Update card"],
                        "eisenhower": "Q1 Do",
                        "schedule_date": "2026-05-23T08:00:00-07:00",
                    }
                ]
            }
        )
        tasks, _ = parse_extractor_output(raw)
        t = tasks[0]
        assert t.do == "Log in to Lovable and update payment method"
        assert t.why == "Service will be suspended if payment remains outstanding."
        assert t.steps == ["Open lovable.dev", "Go to billing settings", "Update card"]

    def test_do_why_steps_default_to_empty(self) -> None:
        raw = json.dumps(
            {
                "tasks": [
                    {
                        "task_name": "Reply to Sarah",
                        "context": "Contract revision due Monday.",
                        "eisenhower": "Q3 Delegate",
                        "schedule_date": "2026-05-23T08:00:00-07:00",
                    }
                ]
            }
        )
        tasks, _ = parse_extractor_output(raw)
        t = tasks[0]
        assert t.do == ""
        assert t.why == ""
        assert t.steps == []

    def test_null_steps_treated_as_empty(self) -> None:
        raw = json.dumps(
            {
                "tasks": [
                    {
                        "task_name": "Check email",
                        "context": "Routine check.",
                        "steps": None,
                        "eisenhower": "Q3 Delegate",
                        "schedule_date": "2026-05-23T08:00:00-07:00",
                    }
                ]
            }
        )
        tasks, _ = parse_extractor_output(raw)
        assert tasks[0].steps == []


class TestMalformedInput:
    @pytest.mark.parametrize(
        "raw,fragment",
        [
            ("this is not json at all", "not valid JSON"),
            ("[1, 2, 3]", "Expected JSON object"),
            (
                '{"tasks":[{"task_name":"x","eisenhower":"Q3 Delegate",'
                '"schedule_date":"2026-05-23T08:00:00-07:00"}]}',
                "missing required fields",
            ),
            (
                '{"tasks":[{"task_name":"x","context":"y",'
                '"eisenhower":"Q4 Auto","schedule_date":"2026-05-23T08:00:00-07:00"}]}',
                "Invalid `eisenhower`",
            ),
        ],
    )
    def test_raises_extractor_error(self, raw: str, fragment: str) -> None:
        with pytest.raises(ExtractorError, match=fragment):
            parse_extractor_output(raw)
