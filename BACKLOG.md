# Virgil — Backlog

Items intentionally deferred. Each entry records **what**, **why it was deferred**, **when to revisit**, and the **source plan** that punted it.

`PLAN.md` is architecture. `NEXTSTEPS.md` is the active checklist. **This file is the parking lot.**

When you pick something up, move it into `NEXTSTEPS.md` (or a new plan) and delete the entry here.

---

## Ingestion / Phase 1

### Multiple ingestion times per day

- **What:** Run the daily briefing more than once per day (e.g. 05:00 morning briefing + 17:00 end-of-day digest).
- **Why deferred:** The current `install_launchd.sh` accepts a single `INGESTION_HOUR` / `INGESTION_MINUTE`. Supporting multiple times means generating a plist `<array>` of `StartCalendarInterval` dicts and parsing a comma-separated `INGESTION_TIMES=05:00,17:00` in bash.
- **When to revisit:** Once you actually want a second briefing slot (probably after Week 2 when Hermes starts producing end-of-day reflections).
- **Source:** `notes_pipeline_polish` plan.

### Cross-timezone scheduling clarity

- **What:** Make it explicit (and possibly enforce) that `INGESTION_HOUR` runs on the Mac's local clock, while `.env` `TIMEZONE` only controls what "today" means inside the script. Today these are independent and can silently disagree.
- **Why deferred:** Two surfaces (Mac System Settings → Date & Time, and `.env` `TIMEZONE`). Reconciling them needs either a startup-time sanity check or doc-only guidance. Documented in a NEXTSTEPS comment for now.
- **When to revisit:** First time you travel or change Mac timezone and the briefing date stamp goes wrong.
- **Source:** `notes_pipeline_polish` plan.

### ~~`src/notion_processor.py` — Daily Briefing -> Draft Tasks bridge~~ **[SHIPPED 2026-05-23]**

- **What shipped:** `src/notion_processor.py` reads a Notion page body, calls an LLM via OpenRouter (not Notion AI — see decision below), parses structured JSON, writes one Draft Task per item. Chained at the end of `src/ingestion.py`. Prompt template at `prompts/notion_processor_extract.md`.
- **Architectural rule preserved:** **Hermes never writes Tasks.** This module is the only writer of new Task rows. Hermes (Phase 2) only reads Tasks with `Status=Approved` and updates Status / System Log / Reflection fields.
- **Smoke harness:** `tests/manual/01_*` through `tests/manual/07_*` — bottom-up checkpoint scripts. See `tests/manual/README.md`.
- **Source:** `phase_15_extractor_build` plan; previously `notes_pipeline_polish` + `PLAN.md` actor/writer rule.

---

## Tasks schema MVP deferrals (2026-05-25)

Columns cut from the MVP Tasks DB. Re-introduce only when the trigger fires.

### Target column (Gmail / Calendar / Notion / Browser / Manual)

- **What:** Select column the extractor set to route Hermes to a Composio toolkit.
- **Why deferred:** Hermes can infer tool from Context; one fewer column for the extractor to get wrong.
- **When to revisit:** Hermes consistently picks wrong tools over 1 week of real runs.
- **Source:** Tasks schema MVP prune session.

### Risk Tier (0-Auto / 1-Draft / 2-Approval / 3-Manual)

- **What:** Separate delegation/approval lane column orthogonal to Eisenhower.
- **Why deferred:** Eisenhower now encodes who acts (Q1/Q2/Q3); safety lives in action shape (drafts not sends).
- **When to revisit:** Need an explicit AI-Auto fire-and-forget lane beyond Q3 safe-action design.
- **Source:** Tasks schema MVP prune session.

### DLQ machinery (Failure Category, Retry Count, Resolution Action, First/Last Failed At, External Action ID)

- **What:** Full dead-letter-queue workflow on Tasks.
- **Why deferred:** No Hermes executor yet; no failures to triage.
- **When to revisit:** Real failures pile up after Phase 2 and manual Failed-status handling isn't enough.
- **Source:** Tasks schema MVP prune session.

### Time Budget column

- **What:** Per-Task execution deadline in seconds (default 120s in executor).
- **Why deferred:** Executor not built; hard-code 120s in Phase 2 first pass.
- **When to revisit:** >1 Task per week exceeds 120s default even after prompt/context fixes.
- **Source:** Tasks schema MVP prune session.

### System Log column

- **What:** Append-only execution trace on the Task row.
- **Why deferred:** Reflection relation to Notes DB (`Kind=Task Reflection`) replaces it for learning; keeps Tasks DB lean.
- **When to revisit:** Reflection-only proves too thin for debugging execution failures.
- **Source:** Tasks schema MVP prune session.

### Q4 Silent Housekeeping pipeline

- **What:** Extractor emits `silent_actions` for Q4 items (archive, extract 2FA codes) instead of only `notes`.
- **Why deferred:** Phase 2 Hermes must be stable first; Q4 still filtered to `notes` at extraction.
- **When to revisit:** Phase 2 Hermes stable for 1+ weeks; user wants AI to handle trivial inbox noise silently.
- **Source:** Tasks schema MVP prune session.

---

These were considered during the architectural planning session and intentionally cut from Phase 2's first build. Each entry records the trigger that should pull it back into NEXTSTEPS.

### Suspended status + Resumption Context + round-robin quantum (Option A execution)

- **What:** Upgrade the Phase 2 executor from deadline-only Time Budget (Option B — current design) to cooperative round-robin (Option A). Add `Status=Suspended`, a `Resumption Context` text field on Tasks, an LLM-based summarization step at quantum expiry, and a hybrid local-file (`logs/working_memory/<task_id>.jsonl`) + Notion field storage for the scratchpad. Loaded back into the LLM prompt on resume.
- **Why deferred:** Single-user, no concurrency pressure in Phase 2. Runaway protection is the only real need, and the deadline pattern covers it in ~10 lines. Option A is ~300 lines plus a per-suspension LLM call. YAGNI until signal appears.
- **When to revisit:** When **legitimate** Tasks routinely exceed their `Time Budget` even after bumps, indicating work that genuinely spans multiple sessions. Or when parallel sub-agents ship (then fairness starts to matter).
- **Source:** `arch_refinements_planning` plan.

### WIP Slot enforcement

- **What:** Re-enable the `WIP Slot` column on the Tasks DB schema and have the executor enforce a max concurrent `Processing` count.
- **Why deferred:** Phase 2 executor is single-threaded (one Task at a time per process). The column would always read 1; there's no concurrency to throttle.
- **When to revisit:** When parallel sub-agents ship (per [PLAN.md](PLAN.md) line 65) or when a second executor process is added. Pairs with **Concurrent Tasks capture** below.
- **Source:** `arch_refinements_planning` plan; original [PLAN.md](PLAN.md) Step 4 of Execution Loop pre-refinement.

### Step budget and token budget for execution

- **What:** Add additional ceilings beyond `Time Budget` — max LLM tool calls per attempt (`step_budget`), max tokens spent per attempt (`token_budget`). Hit any one → Timeout.
- **Why deferred:** Time Budget alone catches the runaway case for typical Phase 2 Tasks. Multi-axis budgeting adds schema + executor complexity without proven signal.
- **When to revisit:** When a single Task burns through meaningful LLM cost without exceeding wall time (e.g. a fast-but-pathological tool-call loop), or when LLM bill is concentrated in a small number of Tasks.
- **Source:** `arch_refinements_planning` plan.

### Concurrent Tasks capture in failure reflections

- **What:** When writing a failure Reflection, include the list of Tasks that were in `Status=Processing` at the same moment. Lets the weekly Learning step detect contention patterns ("Gmail 503s cluster at 8am when 5 Tasks ran concurrently").
- **Why deferred:** Single-threaded Phase 2 executor means concurrent count is always 0 or 1. Field is meaningless until parallelism exists.
- **When to revisit:** Ship alongside **WIP Slot enforcement**.
- **Source:** `arch_refinements_planning` plan.

### Cron-per-Task scheduling (one-shot launchd plists)

- **What:** Alternative to adaptive polling: when a Task's `Schedule Date` is set, the executor (or `notion_processor.py`) generates a one-shot launchd plist that fires exactly at that time. Removes the 60s polling ceiling.
- **Why deferred:** Adaptive polling at 60s ceiling is fine for personal-scale latency. Cron-per-Task adds plist proliferation, orphan-cleanup logic on Task edits/deletes, FDA/launchctl perms on the executor, and timezone/sleep-edge-case complexity. Negative ROI until polling actually bites.
- **When to revisit:** When a Task type needs exact-time precision (e.g. "send at 09:00:00") that 60s polling can't deliver, AND polling itself becomes a real cost or contention problem.
- **Source:** `arch_refinements_planning` plan.

### Per-Target Time Budget defaults / learned tuning

- **What:** Replace the flat 120s default for `Time Budget` with per-Target defaults (e.g. Gmail=60, Calendar=30, Notion=120, Browser=300, Manual=0). Phase 4+ extension: auto-tune defaults from observed completion times in Reflections.
- **Why deferred:** The flat 120s default is a simpler v1 that bins all Tasks the same. Per-Target tuning is premature optimization without Phase 2 completion-time data to back the numbers.
- **When to revisit:** After a few weeks of Phase 2 data, if Reflection clusters show the flat default is consistently too short for one Target and too long for another. Make the numbers data-driven, not assumed.
- **Source:** `arch_refinements_planning` plan.

### Working Memory persistence (file + Notion hybrid)

- **What:** Persist the executor's per-Task scratchpad across attempts. Local append-only file (`logs/working_memory/<task_id>.jsonl`) holds the full reasoning trail; Notion `Resumption Context` field holds an LLM-summarized human-readable snapshot. On resume → load both back into the prompt.
- **Why deferred:** Only relevant under Option A (suspend/resume execution). Phase 2 is deadline-only — Working Memory is in-memory and dies with the execution attempt.
- **When to revisit:** Ship with **Suspended status + Resumption Context + round-robin quantum**.
- **Source:** `arch_refinements_planning` plan.

---

## Other product / infra deferrals

### Notion AI subscription (Plus add-on, or Business tier) — **[DECLINED 2026-05-23]**

- **What was on the table:** Notion Plus + AI add-on ($8 + $8 = $16/mo) or Business ($15/mo) for unlimited Notion AI responses, AI database properties, AI Meeting Notes, Notion Agent.
- **Why declined:** `src/notion_processor.py` now calls an LLM directly via OpenRouter (~$0.05/mo at current usage) instead of routing through Notion AI. The architectural constraint that "Tasks are written by a separate process, not Hermes" is preserved — the extractor process happens to use OpenRouter rather than Notion's hosted LLM. No Notion AI subscription is required for the current architecture.
- **What you give up:** the in-Notion "highlight text → Ask AI" manual fallback (free trial gives ~20 responses per workspace, ever). Manual extraction inside Notion is no longer the daily fallback — `tests/manual/03_extractor_dry_run.py` plays that role and costs ~$0.002 per run.
- **When to revisit:** If you specifically want AI Meeting Notes' in-Notion live transcript UI (vs. the DIY Whisper ingester below), Business at $15/mo gives that. Re-evaluate only when meeting capture is a daily concern.
- **Source:** Phase 1.5 architecture discussion, 2026-05-23.

### DIY meeting ingester (Whisper + local recording)

- **What:** Sibling to `src/ingestion.py`. Watch a folder for new `.m4a`/`.wav` recordings, transcribe via Whisper (local or API), create a `Kind=Meeting Notes` page in Notion. From there, the existing Phase 2 pipeline picks it up — `notion_processor.py` invokes Notion AI to extract Draft Tasks.
- **Why deferred:** No meetings in the Phase 1/2 critical path. Architecture supports it via the existing `Meeting Notes` content kind; just no producer for that kind yet.
- **When to revisit:** When meetings become a recurring source of action items. Cost: ~$3/mo for Whisper API at typical volume, or $0 with local Whisper.
- **Source:** Notion plan-selection conversation; alternative to Business tier upgrade above.

### Conversation Cache (sliding-window conversation memory)

- **What:** A second memory layer alongside Working Memory: holds the last N user/agent turns from interactive chat (Telegram / Slack / CLI), feeds them into Hermes's prompt as `RECENT` context.
- **Why deferred:** Hermes is a background daemon in Phase 2 — no interactive chat surface. Working Memory (per-Task scratchpad) is the only relevant memory layer.
- **When to revisit:** When the Hermes messaging gateway ships ([PLAN.md](PLAN.md) line 64) — Telegram, Slack, or Discord. At that point, conversations are real and a turn cache earns its keep.
- **Source:** `arch_refinements_planning` plan.

---

## Week 2+ (already on the roadmap, listed here for backlog discipline)

These are tracked in `PLAN.md` and `NEXTSTEPS.md` Phase 2. Listed here only so anyone scanning the backlog sees them in one place.

- **Tasks DB end-to-end** — Hermes reads Tasks, executes, updates Status, writes Reflections.
- **Composio integration** — Gmail/Calendar/Notion write tools via MCP, OAuth held by Composio.
- **Hermes Agent install + config** — `pip install hermes-agent`, point at OpenRouter, hook up MCP servers.
- **OpenRouter / LLM routing** — pick default model (current frontrunner: Gemini 2.5 Flash; route up to 2.5 Pro for Risk Tier 2-3).
- **Approval-gated execution** — Tier 1 → Gmail Drafts, Tier 2 → "Approved" status in Notion before send.

---

## Add new entries with this template

```
### Title

- **What:** one or two sentences.
- **Why deferred:** what was in scope of the original plan vs this.
- **When to revisit:** trigger condition or week/phase.
- **Source:** plan name or commit.
```
