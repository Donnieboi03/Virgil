# Virgil — Handoff

> **Read this first when starting a new session.** It captures what's true right now so you don't have to re-derive it from `PLAN.md` + `NEXTSTEPS.md` + git history.
>
> Update this file at the **end** of any session that changed code, config, or docs. Pattern: replace the "Status" block, append to "What shipped" (or rotate older entries into a `## History` section), refresh "What's next" and "Blockers."

---

## Status as of 2026-05-24

- **Phase:** Phase 1.5 code complete. LLM via [`src/llm.py`](src/llm.py) (Gemini or OpenRouter). Test suite reorganized onto pytest (unit + integration + 3 manual scripts). [`PLAN.md`](PLAN.md) swept — "Notion AI" replaced with extractor-process language throughout. Still needs: user runs `pytest`, `pytest --run-integration`, then manual checkpoints 03/06/07; Notion Tasks columns if not yet added.
- **Branch:** `main`
- **Last committed:** `fae5e35` — *Polish ingestion pipeline and close Phase 1.*
- **Working tree:** **very dirty** — multiple uncommitted sessions stacked (arch refinements, Phase 1.5, LLM adapter, test reorg, PLAN sweep). Recommend separate commits per workstream when user asks.
- **Active plan:** [`~/.cursor/plans/test_reorg_plan_md_sweep_5735729e.plan.md`](../../.cursor/plans/test_reorg_plan_md_sweep_5735729e.plan.md) — all todos complete this session.
- **Active scheduler:** launchd job installed (`com.virgil.ingestion` at **08:00** Mac local time). Manual `launchctl start` verified — briefing lands in Notion.

---

## What shipped this session (test reorg + PLAN.md sweep)

**PLAN.md vendor decoupling (user-authorized):**

- Replaced ~20 "Notion AI" references with "extractor process" / `src/notion_processor.py` language.
- Renamed "Notion AI responsibilities" → **Extractor responsibilities**.
- Removed Notion AI cost row; added note that extraction shares OpenRouter/Gemini with Hermes.

**pytest test framework:**

- [`requirements-dev.txt`](requirements-dev.txt) — `pytest>=8.0`, `pytest-cov>=5.0`
- [`pyproject.toml`](pyproject.toml) — pytest config, `integration` marker, `pythonpath = ["."]`
- [`tests/conftest.py`](tests/conftest.py) — `--run-integration` flag, skip integration by default, `fixtures_dir` fixture
- [`tests/unit/`](tests/unit/) — `test_parser.py`, `test_eisenhower.py`, `test_properties.py`, `test_blocks_to_text.py`, `test_extract_from_page.py`
- [`tests/integration/`](tests/integration/) — `test_llm.py`, `test_notion_read.py`, `test_notion_write.py`
- [`tests/fixtures/`](tests/fixtures/) — briefings, llm_responses, notion_blocks captured fixtures
- Deleted promoted manual scripts: `01_llm_hello.py`, `02_notion_read_page.py`, `04_parser_unit.py`, `05_notion_write_one_task.py`
- Kept manual: `03_extractor_dry_run.py`, `06_processor_end_to_end.py`, `07_chained_ingestion.py`
- Updated [`tests/manual/README.md`](tests/manual/README.md) and [NEXTSTEPS.md Phase 1.5 Step 4](NEXTSTEPS.md)

**Day-to-day:**

```bash
pytest                              # unit tier, free
pytest --run-integration            # + LLM + Notion (needs .env, TEST_BRIEFING_PAGE_ID)
python tests/manual/03_extractor_dry_run.py <page_id>   # prompt iteration
```

---

## What shipped earlier (LLM provider adapter)

- [`src/llm.py`](src/llm.py) — `resolve_provider()` + `complete()`; OpenRouter or Gemini.
- [`src/notion_processor.py`](src/notion_processor.py) — `call_llm()` delegates to `llm.complete()`.
- [`src/config.py`](src/config.py) — `GOOGLE_API_KEY`, `GEMINI_MODEL`, optional `LLM_PROVIDER`.
- User verified Gemini path: `provider=gemini`, PASS.

---

## What shipped earlier (Phase 1.5 — extractor code)

- [`src/notion_processor.py`](src/notion_processor.py) — full extractor pipeline + CLI
- [`prompts/notion_processor_extract.md`](prompts/notion_processor_extract.md) — v1 extraction prompt
- [`src/notion_client.py`](src/notion_client.py) — `read_page_blocks`, `blocks_to_text`, `create_task_draft`
- [`src/ingestion.py`](src/ingestion.py) — chained `extract_from_page()` after briefing

---

## What's next

1. **User: activate Phase 1.5.** `pip install -r requirements.txt -r requirements-dev.txt` → LLM key in `.env` → Notion Tasks columns → `TEST_BRIEFING_PAGE_ID` in `.env` for integration tests. See [NEXTSTEPS.md Phase 1.5](NEXTSTEPS.md).
2. **User: run checkpoints.** `pytest` → `pytest --run-integration` → manual 03 → 06 → 07. Iterate prompt between 03 and 06.
3. **Confirm first unattended launchd run** with chained extractor — check `logs/ingestion.log` after 08:00.
4. **Commits when ready** — suggest splitting: (a) PLAN sweep + test reorg, (b) Phase 1.5 + LLM adapter, (c) earlier arch refinements.
5. **Phase 2** — `src/executor.py` daemon; do not start without explicit user ask.

---

## Blockers / open questions

- **LLM key + Notion columns + `TEST_BRIEFING_PAGE_ID`** — only manual gates before full smoke.
- **Refresh-token weekly expiry** — OAuth Testing mode; see NEXTSTEPS Phase 1 troubleshooting.
- **First unattended cron with chained extractor** — not yet confirmed end-to-end.

---

## Notes for the next agent

- **Unit tests are the new minimum bar.** Run `pytest` before any extractor changes.
- **Integration tests need `--run-integration`.** Do not run them in CI yet (no workflow); user runs locally.
- **PLAN.md sweep is done.** Extractor process owns Task creation; no Notion AI subscription.
- **Hermes hasn't been touched.** No Phase 2 code.
- **`.env` contains live secrets.** Never echo contents; only field names.

---

## History

_(Older session summaries get rotated down here.)_

- **2026-05-24 (test reorg + PLAN sweep):** pytest three-tier layout; PLAN.md Notion AI → extractor language. Plan: `test_reorg_plan_md_sweep_5735729e`.
- **2026-05-24 (LLM adapter):** `src/llm.py` dual provider; Gemini verified by user.
- **2026-05-23 (Phase 1.5 build):** `notion_processor.py`, prompts, manual smoke scripts, ingestion chain.
- **2026-05-23 (arch refinements):** Phase 2 spec lockdown in PLAN/NEXTSTEPS/BACKLOG.
- **2026-05-22 (Phase 1 close):** launchd, HN-only news, `fae5e35`.
