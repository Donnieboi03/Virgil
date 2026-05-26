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


# Notion counts rich_text length in UTF-16 code units, not Python code points.
# A single emoji can be 1 Python char but 2 UTF-16 units, so naive text[:2000]
# can still produce 2002 on the wire.
_NOTION_TEXT_LIMIT = 2000


def _utf16_chunks(text: str, limit: int = _NOTION_TEXT_LIMIT) -> list[str]:
    """Split text into chunks of at most `limit` UTF-16 code units.

    Splits at the last whitespace inside each window when possible so we don't
    break mid-word; falls back to a hard cut on the UTF-16 boundary, preserving
    surrogate pairs (we never split a code point in half).
    """
    if not text:
        return [""]
    units = text.encode("utf-16-le")
    if len(units) // 2 <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        encoded = remaining.encode("utf-16-le")
        if len(encoded) // 2 <= limit:
            chunks.append(remaining)
            break
        # Hard ceiling at the UTF-16 boundary, then back off to a whitespace
        # split if there's one in the last ~10% of the window.
        head_bytes = encoded[: limit * 2]
        # Don't slice in the middle of a surrogate pair.
        last_unit = head_bytes[-2:]
        first_byte = last_unit[1] if len(last_unit) == 2 else 0
        if 0xD8 <= first_byte <= 0xDB:
            head_bytes = head_bytes[:-2]
        head = head_bytes.decode("utf-16-le", errors="ignore")
        split_at = head.rfind(" ", max(0, len(head) - limit // 10))
        if split_at > limit // 2:
            chunks.append(head[:split_at])
            remaining = remaining[split_at + 1 :]
        else:
            chunks.append(head)
            remaining = remaining[len(head) :]
    return chunks


def _rt(text: str) -> list[dict[str, Any]]:
    """Build rich_text segments, splitting at Notion's per-segment 2000 UTF-16-unit limit."""
    return [{"type": "text", "text": {"content": chunk}} for chunk in _utf16_chunks(text)]


def _heading(text: str, level: int = 2) -> dict[str, Any]:
    key = f"heading_{level}"
    return {"object": "block", "type": key, key: {"rich_text": _rt(text)}}


def _paragraph(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": _rt(text)},
    }


def _bullet(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": _rt(text)},
    }


def _todo(text: str, *, checked: bool = False) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "to_do",
        "to_do": {"rich_text": _rt(text), "checked": checked},
    }


def _news_blocks(news: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Render news items as one heading_3 per source + one bullet per headline.

    Each item is {source, title, link, summary}. Summary, if present, becomes a
    plain paragraph nested under the heading group (Notion's bulleted_list_item
    cannot have block children via the create endpoint without an extra round
    trip, so we emit the summary as a follow-up indented paragraph).
    """
    if not news:
        return [_paragraph("_No headlines fetched. Check NEWS_RSS_FEEDS in .env._")]

    blocks: list[dict[str, Any]] = []
    current_source = ""
    for item in news:
        if item["source"] != current_source:
            blocks.append(_heading(item["source"], 3))
            current_source = item["source"]
        title_md = f"[{item['title']}]({item['link']})" if item.get("link") else item["title"]
        if item.get("summary"):
            title_md += f" — {item['summary']}"
        blocks.append(_bullet(title_md))
    return blocks


def _inbox_blocks(inbox: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Render inbox items as one paragraph per email — keeps each block well under 2000 chars."""
    if not inbox:
        return [_paragraph("_Inbox zero — no unread or recent messages._")]

    blocks: list[dict[str, Any]] = []
    for msg in inbox:
        subject = msg.get("subject", "(no subject)")
        sender = msg.get("from", "(unknown)")
        snippet = msg.get("snippet", "")
        line = f"{subject} — {sender}"
        if snippet:
            line += f"\n{snippet}"
        blocks.append(_paragraph(line))
    return blocks


def _schedule_blocks(schedule: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Render calendar events as one bullet per event."""
    if not schedule:
        return [_paragraph("_No meetings today._")]

    blocks: list[dict[str, Any]] = []
    for ev in schedule:
        time_label = ev.get("time", "all-day")
        title = ev.get("title", "(untitled)")
        details: list[str] = []
        if ev.get("attendees"):
            details.append(f"with {ev['attendees']}")
        if ev.get("location"):
            details.append(f"@ {ev['location']}")
        suffix = f" ({', '.join(details)})" if details else ""
        blocks.append(_bullet(f"**{time_label}** {title}{suffix}"))
    return blocks


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def create_briefing_note(
    date_str: str,
    news: list[dict[str, Any]],
    inbox: list[dict[str, Any]],
    schedule: list[dict[str, Any]],
) -> str:
    """Create a Daily Briefing row in the Notes DB.

    Accepts structured lists so each item becomes its own block. This keeps
    every rich_text segment well below Notion's 2000 UTF-16-unit per-segment
    limit and makes the page scannable.

    Returns the Notion page ID of the created note.
    """
    cfg = get_config()
    n = _notion()

    body_blocks: list[dict[str, Any]] = [
        _heading("News", 2),
        *_news_blocks(news),
        _heading("Inbox", 2),
        *_inbox_blocks(inbox),
        _heading("Schedule", 2),
        *_schedule_blocks(schedule),
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


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def read_page_blocks(page_id: str) -> list[dict[str, Any]]:
    """Return all top-level children blocks of a page, following pagination.

    Does NOT recurse into nested blocks. For Daily Briefings written by
    create_briefing_note(), the body is flat (headings + paragraphs), so a
    single level is sufficient.
    """
    n = _notion()
    blocks: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        kwargs: dict[str, Any] = {"block_id": page_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        response = _rate_limited_call(n.blocks.children.list, **kwargs)
        blocks.extend(response.get("results", []))
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
        if not cursor:
            break
    return blocks


def blocks_to_text(blocks: list[dict[str, Any]]) -> str:
    """Render a flat list of Notion blocks to a markdown-ish string.

    Handles the block types create_briefing_note() emits (heading_2,
    paragraph) plus the common ones a human might add (heading_1/3,
    bulleted_list_item, numbered_list_item, to_do, quote, code, divider).
    Unknown block types are skipped silently — the LLM doesn't need them.
    """
    lines: list[str] = []
    for block in blocks:
        btype = block.get("type", "")
        payload = block.get(btype, {}) if btype else {}
        text = "".join(
            r.get("plain_text", "") for r in payload.get("rich_text", [])
        )

        if btype == "heading_1":
            lines.append(f"# {text}")
        elif btype == "heading_2":
            lines.append(f"## {text}")
        elif btype == "heading_3":
            lines.append(f"### {text}")
        elif btype == "paragraph":
            lines.append(text)
        elif btype == "bulleted_list_item":
            lines.append(f"- {text}")
        elif btype == "numbered_list_item":
            lines.append(f"1. {text}")
        elif btype == "to_do":
            checked = "x" if payload.get("checked") else " "
            lines.append(f"- [{checked}] {text}")
        elif btype == "quote":
            lines.append(f"> {text}")
        elif btype == "code":
            lang = payload.get("language", "")
            lines.append(f"```{lang}\n{text}\n```")
        elif btype == "divider":
            lines.append("---")
        else:
            continue
        lines.append("")
    return "\n".join(lines).strip()


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def create_task_draft(
    properties: dict[str, Any],
    *,
    children: list[dict[str, Any]] | None = None,
) -> str:
    """Create a row in the Tasks DB with the given Notion property dict.

    Caller is responsible for shaping `properties` to Notion's nested format
    (e.g. {"Task Name": {"title": [...]}, "Status": {"select": {...}}}).
    Optional `children` are page-body blocks (Do / Why / Steps) written at
    create time — implements the closure principle from PLAN.md.
    Returns the new page ID.
    """
    cfg = get_config()
    kwargs: dict[str, Any] = {
        "parent": {"database_id": cfg.tasks_db_id},
        "properties": properties,
    }
    if children:
        kwargs["children"] = children
    page = _rate_limited_call(_notion().pages.create, **kwargs)
    return page["id"]


def rich_text_content(prop: dict[str, Any]) -> str:
    return "".join(r.get("plain_text", "") for r in prop.get("rich_text", []))


def title_content(prop: dict[str, Any]) -> str:
    return "".join(r.get("plain_text", "") for r in prop.get("title", []))
