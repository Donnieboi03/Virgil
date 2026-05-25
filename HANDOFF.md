# Virgil — Handoff

> **Read this first when starting a new session.** It captures what's true right now so you don't have to re-derive it from `PLAN.md` + `NEXTSTEPS.md` + git history.
>
> Update this file at the **end** of any session that changed code, config, or docs. Pattern: replace the "Status" block, append to "What shipped" (or rotate older entries into a `## History` section), refresh "What's next" and "Blockers."

---

## Status as of 2026-05-25

- **Phase:** Phase 1.5 extractor on **MVP Tasks schema** (6 columns). Notion UI migrated by user; code + prompt + tests updated to match. Hermes (Phase 2) not started.
- **Branch:** `main`
- **Last committed:** `f5a157b` — *Ship Phase 1.5 extractor, pytest suite, and PLAN decoupling.*
- **Working tree:** dirty — Tasks schema MVP prune (this session) not yet committed.
- **Active scheduler:** launchd at **08:00** Mac local time.

---

## What shipped this session (Tasks schema MVP prune)

**Locked MVP Tasks schema (6 columns):** Task Name, Context, Status, Eisenhower (Q1 Do / Q2 Schedule / Q3 Delegate), Schedule Date, Reflection → Notes DB.

**Code:**
- [`src/notion_processor.py`](src/notion_processor.py) — dropped Target, Risk Tier, Time Budget; new Eisenhower enum; missing Eisenhower defaults to Q3 Delegate; Q2 leaves Schedule Date blank; writes 5 properties (Reflection empty at extraction).
- [`prompts/notion_processor_extract.md`](prompts/notion_processor_extract.md) — v2 prompt: importance = cognitive engagement; AI-involvement gradient; Q2 prep examples.

**Tests:** fixtures + unit tests updated; `pytest` green (23 passed).

**Docs:** [PLAN.md](PLAN.md) Tasks schema + Eisenhower section; [NEXTSTEPS.md](NEXTSTEPS.md) Phase 0 Database 2 + Step 3; [BACKLOG.md](BACKLOG.md) deferral entries with re-introduction triggers.

**User Notion UI (manual):** Tasks DB pruned; Notes DB has Kind column. User still to: add `Task Reflection` Kind option, delete test/duplicate rows, re-tag Eisenhower on existing Tasks.

---

## What's next

1. **User:** finish Notion cleanup (test rows, duplicate Tasks, Eisenhower tags, `Task Reflection` Kind).
2. **Run:** `pytest` → `pytest --run-integration` → `03_extractor_dry_run.py <page_id>` → review Q1/Q2/Q3 classifications.
3. **If dry-run looks good:** `06_processor_end_to_end.py` then `07_chained_ingestion.py`.
4. **Commit + push** this session's changes.
5. **Phase 2** — do not start without explicit ask.

---

## Blockers

- None code-side. Extractor will fail Notion writes if live DB schema doesn't match MVP (user migrated via Notion AI — should be OK).

---

## Notes for the next agent

- **Eisenhower semantics:** Q1=human now, Q2=AI prep/human later, Q3=AI delegate. Q4 filtered to `notes` only.
- **Hermes filter (Phase 2):** `Approved AND Eisenhower IN (Q2,Q3) AND Schedule_Date <= now()`.
- **Deferred columns** live in BACKLOG with explicit triggers — don't re-add without user override.

---

## History

- **2026-05-24:** test reorg + PLAN sweep + LLM adapter (`f5a157b`).
- **2026-05-23:** Phase 1.5 extractor build, arch refinements.
- **2026-05-22:** Phase 1 close (`fae5e35`).
