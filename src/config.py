from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

load_dotenv(ROOT / ".env")


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is missing or empty. "
            f"Copy .env.example to .env and fill in the value."
        )
    return value


def _optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


class Config:
    # Paths
    root: Path = ROOT
    credentials_path: Path = ROOT / "credentials.json"
    token_path: Path = ROOT / "token.json"
    log_dir: Path = ROOT / "logs"

    # Notion
    notion_token: str
    notes_db_id: str
    tasks_db_id: str
    contacts_db_id: str
    projects_db_id: str
    opportunities_db_id: str
    decisions_db_id: str

    # Google / local
    timezone: str
    news_rss_feeds: list[str]
    news_api_key: str

    # Week 2+ (optional at Week 1)
    composio_api_key: str
    openrouter_api_key: str
    llm_model: str
    hermes_wip_limit: int
    hermes_dlq_threshold: int
    hermes_poll_interval: int

    # Week 5+ (optional until then)
    obsidian_vault_path: Path

    def __init__(self) -> None:
        # Week 1 required
        self.notion_token = _require("NOTION_TOKEN")
        self.notes_db_id = _require("NOTES_DB_ID")
        self.tasks_db_id = _require("TASKS_DB_ID")
        self.timezone = _optional("TIMEZONE", "America/Los_Angeles")

        # Remaining DB IDs are optional until their sprint
        self.contacts_db_id = _optional("CONTACTS_DB_ID")
        self.projects_db_id = _optional("PROJECTS_DB_ID")
        self.opportunities_db_id = _optional("OPPORTUNITIES_DB_ID")
        self.decisions_db_id = _optional("DECISIONS_DB_ID")

        feeds_raw = _optional(
            "NEWS_RSS_FEEDS",
            "https://feeds.arstechnica.com/arstechnica/index,"
            "https://www.politico.com/rss/politicopicks.xml,"
            "https://hnrss.org/frontpage",
        )
        self.news_rss_feeds = [f.strip() for f in feeds_raw.split(",") if f.strip()]
        self.news_api_key = _optional("NEWS_API_KEY")

        # Week 2+ — optional, validated lazily by the modules that need them
        self.composio_api_key = _optional("COMPOSIO_API_KEY")
        self.openrouter_api_key = _optional("OPENROUTER_API_KEY")
        self.llm_model = _optional("LLM_MODEL", "openai/gpt-4.1-mini")

        try:
            self.hermes_wip_limit = int(_optional("HERMES_WIP_LIMIT", "5"))
            self.hermes_dlq_threshold = int(_optional("HERMES_DLQ_THRESHOLD", "20"))
            self.hermes_poll_interval = int(_optional("HERMES_POLL_INTERVAL", "60"))
        except ValueError as exc:
            raise EnvironmentError(f"Numeric env var has non-integer value: {exc}") from exc

        vault_raw = _optional("OBSIDIAN_VAULT_PATH", str(ROOT / "obsidian"))
        self.obsidian_vault_path = Path(vault_raw)

        self.log_dir.mkdir(exist_ok=True)


_instance: Config | None = None


def get() -> Config:
    global _instance
    if _instance is None:
        _instance = Config()
    return _instance
