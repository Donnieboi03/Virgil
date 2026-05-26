# Virgil — Handoff

> **Read this first when starting a new session.** It captures what's true right now so you don't have to re-derive it from `PLAN.md` + `NEXTSTEPS.md` + git history.
>
> Update this file at the **end** of any session that changed code, config, or docs. Pattern: replace the "Status" block, append to "What shipped" (or rotate older entries into a `## History` section), refresh "What's next" and "Blockers."

---

## Status as of 2026-05-25 (late)

- **Phase:** Phase 1.5 extractor on **MVP Tasks schema** (6 columns). Briefing renderer rewritten this session to fix a Notion 2002-char crash and clean up the briefing body. Hermes (Phase 2) not started.
- **Branch:** `main`
- **Last committed:** `ce042d0` — *Prune Tasks schema to MVP six-column design.*
- **Working tree:** dirty — briefing renderer refactor + Gmail/news cleaners (this session) not yet committed.
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

## What's next

1. **Implement v4 extractor + task page body** per PLAN.md "Design principle" → `create_task_draft(children=)` + prompt structured `do`/`why`/`steps[]` (separate session from this doc-only commit).
2. **User:** finish Notion cleanup when ready (test rows, duplicate Tasks, Eisenhower tags, `Task Reflection` Kind option).
3. **If extractor output stays clean for 2–3 days running:** commit + push working tree, then start Phase 2 (Hermes).
4. Optional: fix cosmetic bug in `tests/manual/03_extractor_dry_run.py` (PASS banner says "0 would-be Tasks" while listing candidates — `tasks_written` is 0 in dry-run by design).

---

## Blockers

- None code-side after this session. Extractor will fail Notion writes if live DB schema doesn't match MVP (user migrated via Notion AI — should be OK).

---

## Notes for the next agent

- **Eisenhower semantics:** Q1=human now, Q2=AI prep/human later, Q3=AI delegate. Q4 filtered to `notes` only.
- **Hermes filter (Phase 2):** `Approved AND Eisenhower IN (Q2,Q3) AND Schedule_Date <= now()`.
- **Deferred columns** live in BACKLOG with explicit triggers — don't re-add without user override.

---

## History

- **2026-05-25 (earlier):** Tasks schema MVP prune (`ce042d0`) — 6-column schema, dropped Target/Risk Tier/Time Budget, Eisenhower as cognitive engagement.
- **2026-05-24:** test reorg + PLAN sweep + LLM adapter (`f5a157b`).
- **2026-05-23:** Phase 1.5 extractor build, arch refinements.
- **2026-05-22:** Phase 1 close (`fae5e35`).
