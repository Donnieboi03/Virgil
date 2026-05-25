"""Integration: write one Draft Task with all Phase 1.5 fields, then archive it."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from notion_client import Client

from src.config import get as get_config
from src.notion_client import create_task_draft
from src.notion_processor import ExtractedTask, task_to_notion_properties

pytestmark = pytest.mark.integration


@pytest.fixture
def smoke_task_page_id() -> str:
    cfg = get_config()
    tz = ZoneInfo(cfg.timezone)
    now = dt.datetime.now(tz)
    task = ExtractedTask(
        task_name="SMOKE TEST — pytest integration (auto-archived)",
        context="Created by tests/integration/test_notion_write.py. Should be archived after test.",
        eisenhower="Q3 Delegate",
        schedule_date=now.isoformat(),
    )
    page_id = create_task_draft(task_to_notion_properties(task))
    yield page_id
    Client(auth=cfg.notion_token).pages.update(page_id=page_id, archived=True)


def test_write_task_with_all_fields(smoke_task_page_id: str) -> None:
    assert smoke_task_page_id
    assert len(smoke_task_page_id.replace("-", "")) >= 32
