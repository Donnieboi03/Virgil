from __future__ import annotations

import feedparser
from dataclasses import dataclass

from .config import get as get_config

SUMMARY_MAX = 400
HEADLINES_PER_FEED = 5


@dataclass
class Headline:
    title: str
    link: str
    source: str
    summary: str


def fetch_headlines(limit_per_feed: int = HEADLINES_PER_FEED) -> list[Headline]:
    """Fetch headlines from all configured RSS feeds.

    Returns a flat list of Headline objects, ordered by feed then recency.
    Silently skips feeds that fail to parse so one bad URL doesn't break the briefing.
    """
    cfg = get_config()
    out: list[Headline] = []

    for url in cfg.news_rss_feeds:
        try:
            parsed = feedparser.parse(url)
            source = parsed.feed.get("title") or url
            for entry in parsed.entries[:limit_per_feed]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                raw_summary = entry.get("summary", "") or entry.get("description", "")
                # feedparser often returns HTML in summaries — strip tags naively
                clean_summary = _strip_tags(raw_summary)[:SUMMARY_MAX]
                if title:
                    out.append(Headline(title=title, link=link, source=source, summary=clean_summary))
        except Exception:
            # Don't let a broken feed crash the morning briefing
            continue

    return out


def format_for_briefing(headlines: list[Headline]) -> str:
    if not headlines:
        return "_No headlines fetched. Check NEWS_RSS_FEEDS in .env._"

    lines: list[str] = []
    current_source = ""
    for h in headlines:
        if h.source != current_source:
            if lines:
                lines.append("")
            lines.append(f"**{h.source}**")
            current_source = h.source
        line = f"- [{h.title}]({h.link})"
        if h.summary:
            line += f"\n  {h.summary}"
        lines.append(line)

    return "\n".join(lines)


def _strip_tags(html: str) -> str:
    """Remove HTML tags from a string. Not a full parser — good enough for summaries."""
    import re
    return re.sub(r"<[^>]+>", "", html).strip()
