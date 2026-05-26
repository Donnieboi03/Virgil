"""Unit tests for task_to_notion_properties and task_to_page_blocks."""
from __future__ import annotations

from src.notion_processor import ExtractedTask, task_to_notion_properties, task_to_page_blocks


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


class TestTaskToPageBlocks:
    def _make_task(self, **kwargs) -> ExtractedTask:
        defaults = dict(
            task_name="Fix payment",
            context="Card failed.",
            eisenhower="Q1 Do",
            schedule_date="2026-05-23T08:00:00-07:00",
        )
        defaults.update(kwargs)
        return ExtractedTask(**defaults)

    def test_do_heading_and_paragraph_always_emitted(self) -> None:
        task = self._make_task(do="Log in to Lovable and update card")
        blocks = task_to_page_blocks(task)
        types = [b["type"] for b in blocks]
        assert types[0] == "heading_2"
        assert types[1] == "paragraph"
        text = blocks[0]["heading_2"]["rich_text"][0]["text"]["content"]
        assert text == "Do"
        para = blocks[1]["paragraph"]["rich_text"][0]["text"]["content"]
        assert "Lovable" in para

    def test_do_falls_back_to_task_name_when_blank(self) -> None:
        task = self._make_task(do="")
        blocks = task_to_page_blocks(task)
        para = blocks[1]["paragraph"]["rich_text"][0]["text"]["content"]
        assert para == "Fix payment"

    def test_why_section_omitted_when_empty(self) -> None:
        task = self._make_task(do="Do something", why="")
        blocks = task_to_page_blocks(task)
        types = [b["type"] for b in blocks]
        assert "heading_2" in types
        headings = [b for b in blocks if b["type"] == "heading_2"]
        heading_texts = [h["heading_2"]["rich_text"][0]["text"]["content"] for h in headings]
        assert "Why" not in heading_texts

    def test_why_section_present_when_set(self) -> None:
        task = self._make_task(do="Fix it", why="Service suspends without payment.")
        blocks = task_to_page_blocks(task)
        headings = [b for b in blocks if b["type"] == "heading_2"]
        heading_texts = [h["heading_2"]["rich_text"][0]["text"]["content"] for h in headings]
        assert "Why" in heading_texts

    def test_steps_section_omitted_when_empty(self) -> None:
        task = self._make_task(do="Fix it", steps=[])
        blocks = task_to_page_blocks(task)
        types = [b["type"] for b in blocks]
        assert "to_do" not in types

    def test_steps_emitted_as_to_do_blocks(self) -> None:
        task = self._make_task(do="Fix it", steps=["Open billing", "Update card", "Confirm"])
        blocks = task_to_page_blocks(task)
        todo_blocks = [b for b in blocks if b["type"] == "to_do"]
        assert len(todo_blocks) == 3
        texts = [b["to_do"]["rich_text"][0]["text"]["content"] for b in todo_blocks]
        assert texts[0] == "Open billing"
        assert texts[2] == "Confirm"

    def test_to_do_blocks_default_unchecked(self) -> None:
        task = self._make_task(do="Fix it", steps=["Step one"])
        blocks = task_to_page_blocks(task)
        todo = next(b for b in blocks if b["type"] == "to_do")
        assert todo["to_do"]["checked"] is False
