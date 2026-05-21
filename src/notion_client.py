from __future__ import annotations

import threading
import time
from typing import Any

from notion_client import Client
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import get as get_config

# Notion API hard limit is 3 requests/second per integration.
# All public methods in this module go through _rate_limited_call() to stay under it.
_RATE_LIMIT_PER_SEC = 3
_MIN_INTERVAL = 1.0 / _RATE_LIMIT_PER_SEC

_lock = threading.Lock()
_last_call_time: float = 0.0


def _rate_limited_call(fn: Any, *args: Any, **kwargs: Any) -> Any:
    global _last_call_time
    with _lock:
        now = time.monotonic()
        gap = now - _last_call_time
        if gap < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - gap)
        _last_call_time = time.monotonic()
    return fn(*args, **kwargs)


_client: Client | None = None


def _notion() -> Client:
    global _client
    if _client is None:
        cfg = get_config()
        _client = Client(auth=cfg.notion_token)
    return _client


def _rt(text: str) -> list[dict[str, Any]]:
    """Build a rich_text block from a plain string, capped at Notion's 2000-char limit."""
    return [{"type": "text", "text": {"content": text[:2000]}}]


def _heading(text: str, level: int = 2) -> dict[str, Any]:
    key = f"heading_{level}"
    return {"object": "block", "type": key, key: {"rich_text": _rt(text)}}


def _paragraph(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": _rt(text[:2000])},
    }


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def create_briefing_note(
    date_str: str,
    news_md: str,
    inbox_md: str,
    schedule_md: str,
) -> str:
    """Create a Daily Briefing row in the Notes DB.

    Returns the Notion page ID of the created note.
    """
    cfg = get_config()
    n = _notion()

    body_blocks: list[dict[str, Any]] = [
        _heading("News", 2),
        _paragraph(news_md),
        _heading("Inbox", 2),
        _paragraph(inbox_md),
        _heading("Schedule", 2),
        _paragraph(schedule_md),
    ]

    page = _rate_limited_call(
        n.pages.create,
        parent={"database_id": cfg.notes_db_id},
        properties={
            "Title": {"title": _rt(f"Daily Briefing — {date_str}")},
            "Kind": {"select": {"name": "Daily Briefing"}},
            "Date": {"date": {"start": date_str}},
        },
        children=body_blocks,
    )
    return page["id"]


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def update_page_properties(page_id: str, properties: dict[str, Any]) -> None:
    _rate_limited_call(_notion().pages.update, page_id=page_id, properties=properties)


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def query_database(database_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    response = _rate_limited_call(_notion().databases.query, database_id=database_id, **kwargs)
    return response.get("results", [])


def rich_text_content(prop: dict[str, Any]) -> str:
    return "".join(r.get("plain_text", "") for r in prop.get("rich_text", []))


def title_content(prop: dict[str, Any]) -> str:
    return "".join(r.get("plain_text", "") for r in prop.get("title", []))
