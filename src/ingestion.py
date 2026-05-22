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
import sys
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

from .config import get as get_config
from .google_clients import calendar, gmail
from .news import fetch_headlines, format_for_briefing
from .notion_client import create_briefing_note


def _today_iso(tz: ZoneInfo) -> str:
    return dt.datetime.now(tz).date().isoformat()


def _gmail_triage(tz: ZoneInfo) -> tuple[str, list[dict]]:
    """Return (summary_markdown, raw_thread_list).

    summary_markdown: bullet list of senders + subjects + snippet
    raw_thread_list: raw dicts for downstream use

    Actionability detection lives in src/notion_processor.py (Phase 2),
    which invokes Notion AI on the rendered briefing. This module stays
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
        return "_Inbox zero — no unread or recent messages._", []

    lines: list[str] = []
    raw: list[dict] = []

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
        sender = headers.get("From", "(unknown)")
        subject = headers.get("Subject", "(no subject)")
        snippet = full.get("snippet", "")[:200]
        lines.append(f"- **{subject}**  _{sender}_\n  {snippet}")
        raw.append(
            {
                "id": m["id"],
                "from": sender,
                "subject": subject,
                "snippet": snippet,
            }
        )

    summary = "\n".join(lines)
    return summary, raw


def _calendar_schedule(tz: ZoneInfo, date_str: str) -> str:
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

    if not events:
        return "_No meetings today._"

    lines: list[str] = []
    for e in events:
        start_raw = e["start"].get("dateTime") or e["start"].get("date", "")
        time_label = start_raw[11:16] if "T" in start_raw else "all-day"
        title = e.get("summary", "(untitled)")
        attendees = ", ".join(
            a.get("displayName") or a.get("email", "")
            for a in e.get("attendees", [])[:5]
        )
        location = e.get("location", "")
        details = []
        if attendees:
            details.append(f"with {attendees}")
        if location:
            details.append(f"@ {location}")
        suffix = f"  ({', '.join(details)})" if details else ""
        lines.append(f"- **{time_label}** {title}{suffix}")

    return "\n".join(lines)


def main() -> None:
    cfg = get_config()
    tz = ZoneInfo(cfg.timezone)
    date_str = _today_iso(tz)

    print(f"[ingestion] {date_str} — starting")

    print("[ingestion] fetching news...")
    headlines = fetch_headlines()
    news_md = format_for_briefing(headlines)

    print("[ingestion] fetching inbox...")
    inbox_md, _raw_threads = _gmail_triage(tz)

    print("[ingestion] fetching calendar...")
    schedule_md = _calendar_schedule(tz, date_str)

    print("[ingestion] writing to Notion...")
    page_id = create_briefing_note(
        date_str=date_str,
        news_md=news_md,
        inbox_md=inbox_md,
        schedule_md=schedule_md,
    )

    print(f"[ingestion] done — briefing page {page_id}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ingestion] FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
