"""Daily briefing entrypoint — Week 1 vertical slice.

Run manually:
    python -m src.ingestion

Scheduled via launchd at 05:00 daily:
    scripts/install_launchd.sh

What it does:
1. Fetches today's top headlines from configured RSS feeds.
2. Triages unread Gmail from the last 24 hours.
3. Fetches today's Google Calendar events.
4. Writes a Daily Briefing note to the Notion Notes DB.
"""
from __future__ import annotations

import base64
import datetime as dt
import html
import re
import sys
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any
from zoneinfo import ZoneInfo

from .config import get as get_config
from .google_clients import calendar, gmail
from .news import fetch_headlines
from .notion_client import create_briefing_note

# Marketing emails inject hundreds of zero-width / combining padding characters
# into preheaders to inflate Gmail's snippet preview. Strip them so we don't
# blow past Notion's per-block limit on noise.
_INVISIBLE = re.compile(
    r"[\u034F\u00AD\u061C\u115F\u1160\u17B4\u17B5\u180B-\u180E"
    r"\u200B-\u200F\u202A-\u202E\u2060-\u2064\u206A-\u206F\u3164\uFEFF\uFFA0]+"
)


def _clean_text(s: str) -> str:
    """Decode HTML entities, strip invisible padding chars, collapse whitespace."""
    s = html.unescape(s)
    s = _INVISIBLE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _clean_sender(raw: str) -> str:
    """Return display name if present, else the local-part of the email address."""
    name, addr = parseaddr(raw or "")
    name = _clean_text(name)
    if name:
        return name
    if addr and "@" in addr:
        return addr.split("@", 1)[0]
    return addr or "(unknown)"


def _today_iso(tz: ZoneInfo) -> str:
    return dt.datetime.now(tz).date().isoformat()


def _gmail_triage(tz: ZoneInfo) -> list[dict[str, Any]]:
    """Return a list of cleaned inbox records.

    Each record: {id, from, subject, snippet}. Strips invisible padding chars
    that marketing emails inject to inflate preview snippets, and reduces
    sender to a display name (or email local-part) for readability.

    Actionability detection lives in src/notion_processor.py (Phase 2),
    which invokes the LLM on the rendered briefing. This module stays
    a dumb pipeline — no regex heuristics, no precomputed flags.
    """
    svc = gmail()
    resp = (
        svc.users()
        .messages()
        .list(
            userId="me",
            q="in:inbox (is:unread OR newer_than:1d)",
            maxResults=10,
        )
        .execute()
    )
    msgs = resp.get("messages", [])
    if not msgs:
        return []

    out: list[dict[str, Any]] = []
    for m in msgs:
        full = (
            svc.users()
            .messages()
            .get(
                userId="me",
                id=m["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )
        headers = {h["name"]: h["value"] for h in full["payload"].get("headers", [])}
        out.append(
            {
                "id": m["id"],
                "from": _clean_sender(headers.get("From", "")),
                "subject": _clean_text(headers.get("Subject", "(no subject)")),
                "snippet": _clean_text(full.get("snippet", ""))[:200],
            }
        )
    return out


def _calendar_schedule(tz: ZoneInfo, date_str: str) -> list[dict[str, Any]]:
    """Return a list of cleaned calendar event records.

    Each record: {time, title, attendees, location}.
    """
    svc = calendar()
    day = dt.date.fromisoformat(date_str)
    start = dt.datetime.combine(day, dt.time.min, tzinfo=tz).isoformat()
    end = dt.datetime.combine(day, dt.time.max, tzinfo=tz).isoformat()

    events = (
        svc.events()
        .list(
            calendarId="primary",
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
        .get("items", [])
    )

    out: list[dict[str, Any]] = []
    for e in events:
        start_raw = e["start"].get("dateTime") or e["start"].get("date", "")
        time_label = start_raw[11:16] if "T" in start_raw else "all-day"
        attendees = ", ".join(
            a.get("displayName") or a.get("email", "")
            for a in e.get("attendees", [])[:5]
        )
        out.append(
            {
                "time": time_label,
                "title": e.get("summary", "(untitled)"),
                "attendees": attendees,
                "location": e.get("location", ""),
            }
        )
    return out


def main() -> None:
    cfg = get_config()
    tz = ZoneInfo(cfg.timezone)
    date_str = _today_iso(tz)

    print(f"[ingestion] {date_str} — starting")

    print("[ingestion] fetching news...")
    headlines = fetch_headlines()
    news = [
        {"source": h.source, "title": h.title, "link": h.link, "summary": h.summary}
        for h in headlines
    ]

    print("[ingestion] fetching inbox...")
    inbox = _gmail_triage(tz)

    print("[ingestion] fetching calendar...")
    schedule = _calendar_schedule(tz, date_str)

    print("[ingestion] writing to Notion...")
    page_id = create_briefing_note(
        date_str=date_str,
        news=news,
        inbox=inbox,
        schedule=schedule,
    )

    print(f"[ingestion] briefing page {page_id}")

    # Phase 1.5: chained extraction. The briefing has landed at this point,
    # so any extractor failure degrades gracefully — you fall back to manual
    # extraction in Notion for the day. We intentionally swallow every
    # exception here for that reason.
    try:
        from .notion_processor import extract_from_page

        print("[ingestion] extracting Draft Tasks...")
        result = extract_from_page(page_id)
        print(
            f"[ingestion] extracted {result.tasks_written} Draft Tasks"
            + (f" — {result.skipped_notes}" if result.skipped_notes else "")
        )
    except Exception as exc:
        print(
            f"[ingestion] WARN extractor failed (briefing already landed): {exc}",
            file=sys.stderr,
        )

    print("[ingestion] done")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ingestion] FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
