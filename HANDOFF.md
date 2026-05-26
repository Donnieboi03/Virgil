# Virgil — Handoff

> **Read this first when starting a new session.** It captures what's true right now so you don't have to re-derive it from `PLAN.md` + `NEXTSTEPS.md` + git history.
>
> Update this file at the **end** of any session that changed code, config, or docs. Pattern: replace the "Status" block, append to "What shipped" (or rotate older entries into a `## History` section), refresh "What's next" and "Blockers."

---

## Status as of 2026-05-25 (evening)

- **Phase:** Phase 1.5 extractor on **MVP Tasks schema** (6 columns). v4 extractor with closure principle (Do/Why/Steps page body) fully shipped. Hermes (Phase 2) not started.
- **Branch:** `main`
- **Last committed:** `ce042d0` — *Prune Tasks schema to MVP six-column design.*
- **Working tree:** dirty — all changes from this session and the prior session not yet committed (commit_push is the final todo).
- **Active scheduler:** launchd at **08:00** Mac local time.

---

## What shipped this session (briefing renderer + ingestion cleanup + prompt v3 + PLAN principle)

**Three sub-shipments, all in one working tree, none committed yet.**

### A. Briefing renderer (fixed 2002-char Notion crash)

`python -m src.ingestion` was aborting before the extractor ran with `body.children[3].paragraph.rich_text[0].text.content.length should be ≤ 2000, instead was 2002` — the Inbox section was one giant paragraph and Notion counts in UTF-16 code units. Also the briefing body was bloated by HN's metadata footers and marketing-email zero-width padding.

- [`src/notion_client.py`](src/notion_client.py) — new `_utf16_chunks()` UTF-16-safe splitter (surrogate-pair aware); `_rt()` now returns multiple segments instead of truncating; `create_briefing_note()` rewritten to take **structured lists** (`news`, `inbox`, `schedule`) and emit **one block per item** (`heading_3` per source + `bulleted_list_item` per headline for News, one `paragraph` per email for Inbox, one bullet per event for Schedule). New helpers `_bullet()`, `_news_blocks()`, `_inbox_blocks()`, `_schedule_blocks()`.
- [`src/ingestion.py`](src/ingestion.py) — `_gmail_triage()` and `_calendar_schedule()` now return structured records instead of pre-joined markdown; new `_clean_text()` strips invisible/zero-width padding (`\u200B`, `\u034F`, `\uFEFF`, etc. — Wispr/Lovable-style preheader noise) and decodes HTML entities (`&#39;` → `'`, `&#8230;` → `…`, `&amp;` → `&`); new `_clean_sender()` reduces senders to display name or email local-part via `parseaddr`.
- [`src/news.py`](src/news.py) — new `_clean_summary()` drops HN-style metadata lines (`Article URL:`, `Comments URL:`, `Points:`, `# Comments:`) and decodes HTML entities; titles now `html.unescape()`'d in `fetch_headlines()`.

### B. News feeds

- [`.env`](.env) + [`.env.example`](.env.example) — `NEWS_RSS_FEEDS` now includes Ars Technica and The Verge alongside HN so the briefing has real editorial blurbs for the extractor to work with.

### C. Extractor prompt v3 (skeptical defaults)

First live extraction on the new briefing produced 6 Draft Tasks, only 2 of which were genuine signal. The other 4 were marketing emails (Kraken transfer bonus, Educative sale, Squirrelites merch, lablab hackathon) the LLM treated as Q3 Delegate. Root causes were three prompt issues, all addressed in v3:

- [`prompts/notion_processor_extract.md`](prompts/notion_processor_extract.md) — bumped header to v3.
  - **Flipped default:** unclear items now route to Q4 skip path instead of fabricating Q3 ("a false-positive Task is worse than a missed one").
  - **Tightened Q3 Delegate:** explicit list of things AI may NOT do (move money, make purchases, sign up for services, accept invites, commit to anything new). Verbs like "consider/review/decide/evaluate" are flagged as human cognition, not delegatable.
  - **Expanded Q4 SKIP RULE:** broke skip categories into 6 named buckets (Promotional, Newsletters/digests, Unsolicited pitches, Informational, Transactional confirmations, Verification codes) with concrete keyword examples. Added the "would deleting it unread cause harm?" heuristic.
  - **New Example 3:** marketing-heavy inbox modeled on today's actual briefing — skips Kraken/Educative/Squirrelites/Google Play receipt, keeps only Lovable payment (Q1) and BNY office hours prep (Q2). Old Example 3 renumbered to Example 4.

**Tests:** pytest green (23 unit passed) across all three sub-shipments. Smoke-tested helpers in isolation (UTF-16 chunker, padding stripper, HN metadata stripper, `html.unescape` on both `_clean_text` and `_clean_summary`). Prompt changes do not affect unit fixtures.

### D. Design principle: closure over collection (PLAN.md)

Documented the product rationale for why Virgil must produce **closures**, not another inbox — inserted as a top-level section in [PLAN.md](PLAN.md) between System overview and Layer descriptions. Anchored in two David Allen *Getting Things Done* (2001) quotes (trusted external capture; projects vs action steps). Frames the two levers: **Eisenhower filter** (volume, extractor v3) and **action decomposition** (per-item cost, planned v4). Implementation boundary locked: decomposition in **task page body** (block children), not a new DB column; Skills stay Obsidian-only. No code changes in this sub-shipment.

---

## What shipped this session (v4 extractor + cost report)

### E. Prompt v4 — closure: Do / Why / Steps

[`prompts/notion_processor_extract.md`](prompts/notion_processor_extract.md) — bumped header to v4.
- Output schema for `tasks` extended with `do` (one-line imperative), `why` (optional 1 sentence), `steps` (optional array, max 5; **only when source states the procedure explicitly**).
- `context` redefined as the scannable table summary only — detail belongs in the page body.
- **Hard rule 6:** "Never invent `steps`. If the source does not state how to act, omit `steps` or use `[]`. Do not fabricate button names, menu paths, or URLs."
- Examples 1–3 updated to show new field shape end-to-end. Closure rule stated explicitly.

### F. ExtractedTask dataclass + parser

[`src/notion_processor.py`](src/notion_processor.py):
- `ExtractedTask` extended with `do: str = ""`, `why: str = ""`, `steps: list[str] = field(default_factory=list)`.
- `parse_extractor_output()` reads new optional fields with safe defaults (empty string, empty list); `steps=None` normalised to `[]`.
- `apply_eisenhower_defaults()` forwards the new fields through both branches.
- New `task_to_page_blocks(task) -> list[dict]`: emits `Heading2("Do") + Paragraph(do)` always; `Heading2("Why") + Paragraph(why)` when why non-empty; `Heading2("Steps") + to_do per step` when steps non-empty. Falls back to `task_name` when `do` is blank.
- `extract_from_page()` live path calls `create_task_draft(properties, children=body_blocks)`.
- Dry-run print extended to show do/why/steps.

### G. notion_client.py — create_task_draft children support

[`src/notion_client.py`](src/notion_client.py):
- `create_task_draft(properties, *, children=None)` — new optional kwarg; passed to `pages.create` when non-empty. `_todo()` helper already existed.

### H. Fixtures + unit tests

- `tests/fixtures/llm_responses/happy_path.json` + `malformed_fenced.json` regenerated with `do`/`why`/`steps`.
- `tests/unit/test_parser.py` — 3 new tests: `do`/`why`/`steps` parsed, default to empty, `steps=None` treated as `[]`.
- `tests/unit/test_properties.py` — 7-test `TestTaskToPageBlocks` class covering all block-shape cases.
- `tests/unit/test_extract_from_page.py` — new `test_live_run_passes_children_blocks`: asserts `create_task_draft` called with `children=` kwarg containing `heading_2` + `paragraph`.
- **34 unit tests, all green.**

### I. Part B — token / cost report

[`src/llm.py`](src/llm.py):
- New `Usage` dataclass (`provider`, `model`, `prompt_tokens`, `completion_tokens`, `total_tokens` property).
- New `complete_with_usage()` — mirrors `complete()` but returns `(text, Usage)`. Pulls `response.usage` (OpenRouter) or `response.usage_metadata` (Gemini). `complete()` unchanged.

[`scripts/llm_pricing.py`](scripts/llm_pricing.py):
- `PRICING` dict: `(input_$/1M, output_$/1M)` for Gemini Flash/Pro variants + common OpenRouter models (Claude Sonnet/Haiku, GPT-4o/mini, Llama 3.1).
- `cost_usd(model, prompt_tokens, completion_tokens) -> float` — raises `KeyError` with a helpful "add it to PRICING" message for unknown models.

[`tests/manual/08_cost_report.py`](tests/manual/08_cost_report.py):
- `python tests/manual/08_cost_report.py <page_id>` fetches page, calls LLM with `complete_with_usage()`, parses tasks, prints a cost table (model, tokens, $/run, $/month projected, tasks emitted, skipped notes).
- **Live result on today's briefing:** model=gemini-2.5-flash, prompt=4929, completion=495, total=5424, cost=$0.001036, projected=$0.031/month.

---

## What's next

1. **User:** finish Notion cleanup when ready (test rows, duplicate Tasks, Eisenhower tags, `Task Reflection` Kind option).
2. **Run `python -m src.ingestion`** end-to-end and open a created task in Notion to confirm Do/Why/Steps render as checkboxes.
3. **If extractor output stays clean for 2–3 days running:** start Phase 2 (Hermes).
4. Optional: fix cosmetic bug in `tests/manual/03_extractor_dry_run.py` (PASS banner says "0 would-be Tasks" while listing candidates — `tasks_written` is 0 in dry-run by design).

---

## Blockers

- None code-side after this session. Extractor will fail Notion writes if live DB schema doesn't match MVP (user migrated via Notion AI — should be OK).

---

## Notes for the next agent

- **Eisenhower semantics:** Q1=human now, Q2=AI prep/human later, Q3=AI delegate. Q4 filtered to `notes` only.
- **Hermes filter (Phase 2):** `Approved AND Eisenhower IN (Q2,Q3) AND Schedule_Date <= now()`.
- **Deferred columns** live in BACKLOG with explicit triggers — don't re-add without user override.
- **Steps render concern (revisit when Hermes ships):** v4 will render task-page-body Steps as `to_do` checkboxes for all quadrants (closure-native; matches GTD). This is fine pre-Hermes because the human reads every page body anyway. Once Hermes is live executing Q3, `to_do` for Q3 creates an ambiguity:
  - If Hermes ticks each step as it works, that's an extra Notion write per step (rate-limit cost) with no real signal — `Status` + `System Log` already tell the story.
  - If Hermes doesn't tick them, closed Q3 tasks show permanently-unticked checkboxes, which scans as unfinished work.
  - **Fix at that point:** branch the block type in `create_task_draft()` on `eisenhower` — `to_do` for Q1/Q2 (human executes, ticks closure), `numbered_list_item` read-only for Q3 (Hermes follows the recipe; human is reviewing, not ticking). Cheap, reversible change; deferred until Hermes exists and we have real usage data on whether the human actually ticks boxes.

---

## History

- **2026-05-25 (evening):** v4 extractor + closure principle + cost report — this session.
- **2026-05-25 (earlier):** Briefing renderer + Gmail/news cleaners + prompt v3 + PLAN.md closure principle doc — working tree not yet committed (included in upcoming commit).
- **2026-05-25 (morning):** Tasks schema MVP prune (`ce042d0`) — 6-column schema, dropped Target/Risk Tier/Time Budget, Eisenhower as cognitive engagement.
- **2026-05-24:** test reorg + PLAN sweep + LLM adapter (`f5a157b`).
- **2026-05-23:** Phase 1.5 extractor build, arch refinements.
- **2026-05-22:** Phase 1 close (`fae5e35`).
