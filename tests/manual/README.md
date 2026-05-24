# Manual checkpoint scripts

Three scripts remain here for flows that need **human judgement** — prompt quality review, live Draft inspection, and full pipeline verification. Automated coverage lives in `tests/unit/` (fast, free) and `tests/integration/` (opt-in, hits real APIs).

## Test tiers

| Tier | Location | Command | When to run |
|---|---|---|---|
| **Unit** | `tests/unit/` | `pytest` | Every code change. No `.env` required. |
| **Integration** | `tests/integration/` | `pytest --run-integration` | After `.env` is set; costs ~$0.01/run. |
| **Manual** | `tests/manual/` (this folder) | `python tests/manual/03_...` | Prompt iteration, eyeballing Drafts, cron check. |

Install dev deps once:

```bash
cd /Users/donnieb/Desktop/Code/Virgil
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Run each manual script **from the repo root** (scripts add the root to `sys.path` via `_bootstrap.py`):

```bash
python tests/manual/03_extractor_dry_run.py <page_id>
```

If you see `ModuleNotFoundError: No module named 'src'`, you are not in the repo root or the venv is wrong.

## Automated checkpoints (pytest)

Run these before the manual scripts:

```bash
# Unit tier — fast, free, no API keys
pytest

# Integration tier — needs .env + TEST_BRIEFING_PAGE_ID for Notion read test
pytest --run-integration
```

Integration tests cover what used to be scripts `01`, `02`, and `05`:

- `tests/integration/test_llm.py` — LLM reachable (Gemini or OpenRouter)
- `tests/integration/test_notion_read.py` — read + render a real briefing page
- `tests/integration/test_notion_write.py` — write one Draft Task, archive in teardown

Set `TEST_BRIEFING_PAGE_ID` in `.env` to a Daily Briefing page ID for the Notion read test.

## Manual scripts (human judgement required)

| Script | Purpose | Prereqs |
|---|---|---|
| `03_extractor_dry_run.py <page_id>` | Full LLM round-trip, prints would-be Tasks, writes nothing | Unit + integration green; LLM key in `.env` |
| `06_processor_end_to_end.py <page_id>` | Full processor against real briefing, writes real Drafts | 03 output looks good |
| `07_chained_ingestion.py` | `python -m src.ingestion` produces briefing + Drafts | 06 Drafts look right |

Recommended order: `pytest` → `pytest --run-integration` → `03` → `06` → `07`.

## Get a briefing page ID

1. Open any Daily Briefing in Notion
2. Click **Share** → **Copy link**
3. The URL ends with a 32-character hex page ID (may include dashes)

Example URL:

```
https://www.notion.so/yourws/Daily-Briefing-2026-05-22-abcdef1234567890abcdef1234567890
                                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

Paste into `.env` as `TEST_BRIEFING_PAGE_ID=...` for integration tests, or pass directly to manual scripts.

## When something fails

**pytest unit failures** — code or fixture bug; fix in `src/` or `tests/unit/`.

**Integration failures:**

- **401 / auth error on LLM** → check `GOOGLE_API_KEY` or `OPENROUTER_API_KEY`, and `GEMINI_MODEL` / `LLM_MODEL`
- **Notion unauthorized** → `NOTION_TOKEN` issue
- **Notion 404 on read** → wrong page ID, or integration not connected to the page's parent DB
- **Notion validation_error on write** → Tasks DB missing a column (`Schedule Date`, `Time Budget`, etc.)

**Manual script failures:**

- **03 parse error** → tune `prompts/notion_processor_extract.md` and re-run
- **06 partial write** → delete bad Drafts in Notion before re-running

## Prompt iteration loop

```bash
python tests/manual/03_extractor_dry_run.py <yesterday's briefing page id>
# review output, edit prompts/notion_processor_extract.md
python tests/manual/03_extractor_dry_run.py <same page id>
# repeat until dry-run output looks good, then run 06
```

Dry-run cost: ~$0.002 per round trip (Gemini Flash or GPT-4.1-mini).
