# Virgil — Handoff

> **Read this first when starting a new session.** It captures what's true right now so you don't have to re-derive it from `PLAN.md` + `NEXTSTEPS.md` + git history.
>
> Update this file at the **end** of any session that changed code, config, or docs. Pattern: replace the "Status" block, append to "What shipped" (or rotate older entries into a `## History` section), refresh "What's next" and "Blockers."

---

## Status as of 2026-05-22

- **Phase:** Phase 1 **complete** (OAuth, briefing, launchd at 08:00; manual `launchctl start` verified in Notion). Phase 1.5 (Notion AI → Draft Tasks bridge) is next. Phase 2 not started.
- **Branch:** `main`
- **Last committed:** `b91b853` — *Update NEXTSTEPS for Phase 0 completion and Phase 1 handoff.*
- **Working tree:** **dirty** — the `notes_pipeline_polish` plan has been executed but not yet committed. Modified: `.env.example`, `NEXTSTEPS.md`, `scripts/com.virgil.ingestion.plist`, `scripts/install_launchd.sh`, `src/config.py`, `src/ingestion.py`. Untracked: `AGENTS.md`, `BACKLOG.md`, `HANDOFF.md` (this file).
- **Active plan:** [`~/.cursor/plans/notes_pipeline_polish_58473c71.plan.md`](../../.cursor/plans/notes_pipeline_polish_58473c71.plan.md) — all 6 todos complete, awaiting commit.
- **Active scheduler:** launchd job **installed** (`com.virgil.ingestion` at **08:00** Mac local time). Manual `launchctl start` verified — briefing lands in Notion. First unattended 08:00 run not yet confirmed.

---

## What shipped this session

Notes pipeline polish (pre-Tasks):

- **News:** Trimmed default RSS feeds to HackerNews only (`https://hnrss.org/frontpage`) in `src/config.py`, `.env.example`, and `.env`. Multiple feeds still supported via comma-separated list.
- **Inbox query:** `src/ingestion.py` now uses `q="in:inbox (is:unread OR newer_than:1d)"` with `maxResults=10`. Old `is:unread AND newer_than:1d` was too narrow.
- **Removed action-keyword regex:** Deleted `_ACTION_KEYWORDS` tuple and `flagged` logic from `src/ingestion.py`. The replacement is `src/notion_processor.py` (Phase 2) invoking Notion AI — **not Hermes**.
- **Customizable schedule:** New `INGESTION_HOUR` / `INGESTION_MINUTE` env vars (default `5` / `0`). `scripts/install_launchd.sh` sources `.env` in a subshell (no parent-env leak), validates ranges, substitutes into the plist template (`HOUR_PLACEHOLDER` / `MINUTE_PLACEHOLDER`), and prints the actual schedule in its summary.
- **NEXTSTEPS overhaul:** Phase 1 Steps 1-5 ticked; Step 5 has a Troubleshooting block (`access_denied` test-user fix, 7-day refresh-token expiry, `credentials.json` path); Step 6 now references the schedule env vars.
- **New Phase 1.5 section in NEXTSTEPS:** "Notion AI → Draft Tasks bridge" — 6 steps covering Notion AI enablement, Tasks DB sharing, manual day-one fallback, prompt template spec, invocation pattern decision, BACKLOG pointer.
- **Phase 2 intro callout in NEXTSTEPS:** Reminds the next agent that Hermes never creates Tasks.
- **BACKLOG:** Replaced the (mis-wired) "LLM-based inbox triage" entry with `src/notion_processor.py — Notion AI bridge for Daily Briefing → Draft Tasks`. Existing entries for multi-time scheduling and cross-timezone clarity preserved.

Repo / agent operating layer:

- **`AGENTS.md`:** New file at root. Defines the session ritual (read HANDOFF first), the four-doc taxonomy, architectural hard rules from `PLAN.md`, conventions (code, secrets, commits, plans, scheduling), and the project's negative space.
- **`HANDOFF.md`:** This file. Seeded with current state.

---

## What's next

In rough order:

1. **Commit the polish work** (still uncommitted). Two natural commits: pipeline changes vs. `AGENTS.md` + `HANDOFF.md`.
2. **Confirm first unattended launchd run** — check `logs/ingestion.log` after 08:00 tomorrow; tick Week 1 criterion in `NEXTSTEPS.md` if the briefing auto-appears.
3. **Phase 1.5 walkthrough.** Manual extraction test (Phase 1.5 Step 3) to inform the prompt template (Step 4).
4. **Phase 2 Step 0 = build `src/notion_processor.py`.** Tracked in `BACKLOG.md`. Must happen before Composio/Hermes work or Hermes polls an empty queue.

---

## Blockers / open questions

- **Notion AI automation mechanism is undecided.** The "external helper script" path was chosen, but the exact invocation (chained from `ingestion.py` vs. its own launchd job) is still open. Pending decision noted in NEXTSTEPS Phase 1.5 Step 5.
- **Refresh-token weekly expiry.** OAuth consent screen is in Testing mode, so `token.json` rotates every 7 days. Cron will silently start failing — workaround documented in NEXTSTEPS Phase 1 Step 5 Troubleshooting. Long-term fix: publish the app (no verification required for a single-user app with `gmail.readonly` + `calendar.readonly`), but not blocking.
- **Notion AI subscription not yet active.** Phase 1.5 cannot fully validate until the user enables it ($10/mo, per Phase 0 Step 5). Documented but pending.

---

## Notes for the next agent

- **Inbox query semantics changed.** Old: "unread AND ≤24h." New: "unread OR ≤24h, max 10." On a quiet day this can dredge old unread items; on a busy day, the cap of 10 may cut off real recent traffic. Watch user feedback the first week and consider adding a separate "Recent" and "Backlog (unread)" section split if it bites.
- **`.env` source contains live `NOTION_TOKEN`.** Don't echo `.env` contents back in chat; only show field names. The `install_launchd.sh` subshell pattern was deliberately chosen to avoid leaking other env vars into the parent shell.
- **Hermes hasn't been touched.** No Phase 2 code exists. Don't import `composio` or `hermes_agent` anywhere — those packages aren't installed and `pip install -r requirements.txt` will not pull them.
- **`PLAN.md` is read-only.** If the user asks you to update architecture, push back and ask whether they want a NEXTSTEPS/BACKLOG entry instead. Real PLAN edits require an explicit "yes, edit PLAN."
- **OAuth + briefing cycle confirmed working end-to-end** as of the latest run — `token.json` exists, briefing appeared in Notion Notes DB with all three sections populated. If that breaks, first check OAuth test-user list and `credentials.json` location before anything else.

---

## History

_(Older session summaries get rotated down here. Keep the Status / What shipped / What's next blocks above lean.)_

- **2026-05-22 (Phase 0 + Phase 1 manual setup):** Notion DBs created (Notes + Tasks); integration token + DB sharing; Google Cloud project, OAuth consent screen (Testing mode + test user), `credentials.json` downloaded; venv created; first `python -m src.ingestion` succeeded after fixing `access_denied` by adding the Gmail to Test users. Commits: `78362f6`, `b91b853`.
