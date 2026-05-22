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

### `src/notion_processor.py` — Notion AI bridge for Daily Briefing -> Draft Tasks

- **What:** Standalone Python script (**not Hermes**) that runs after `src/ingestion.py`, calls the Notion AI API on the newly created Daily Briefing page, extracts action items, and writes them to the Tasks DB as rows with `Status=Draft`. Uses the prompt template from `prompts/notion_processor_extract.md` (also to be created).
- **Why deferred:** Belongs in Phase 2 alongside the rest of the Tasks pipeline. Requires Notion AI subscription + a calibrated prompt template (see NEXTSTEPS Phase 1.5 Step 4 for the spec). Removing the action-keyword regex in `src/ingestion.py` creates a temporary gap (no automatic flagging) that the manual fallback in NEXTSTEPS Phase 1.5 Step 3 covers.
- **When to revisit:** **Phase 2 Step 0, before Composio/Hermes install.** Tasks DB must start populating before Hermes is useful — otherwise Hermes polls an empty queue.
- **Architectural constraint:** **Hermes never writes Tasks** (`PLAN.md` lines 185, 195-199). This script and humans are the only writers. Hermes only reads Tasks with `Status=Approved` and updates `Status` / `System Log` / Reflection notes.
- **Open decision:** chained from `src/ingestion.py` vs. separate launchd job — see NEXTSTEPS Phase 1.5 Step 5.
- **Source:** `notes_pipeline_polish` plan; `PLAN.md` lines 89, 185, 195-199, 327-332.

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
