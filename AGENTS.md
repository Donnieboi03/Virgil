# Virgil — Agent Operating Guide

This file is read automatically by Cursor, Codex, Claude Code, and other AI coding agents. It tells you (the agent) the project's taxonomy, hard rules, and session ritual. Read it before doing anything else.

**Virgil** is a personal cognitive operating system: morning ingestion (news + Gmail + Calendar) lands a Daily Briefing in Notion, Notion AI parses briefings into Draft Tasks, and Hermes (Week 2+) executes Approved Tasks via Composio. Architecture lives in `PLAN.md`.

---

## Session ritual

Every session, in order:

1. **Read `HANDOFF.md` first.** It records the last session's state — what shipped, what's blocked, what's queued. Skip this and you'll re-derive context the user already wrote down.
2. **Glance at `NEXTSTEPS.md`** for the active checklist. Confirm the next concrete step matches what the user is asking for.
3. **Only then** start exploring code or proposing changes.

At the **end** of any session that changed code, config, or docs:

- Update `HANDOFF.md` with: what shipped, current branch/commit, working-tree state, what's next, and any blockers or subtle gotchas the next agent needs.

---

## Documentation ledger

The four working docs and their roles. Treat the edit policy as a hard rule.

| File | Role | Edit policy |
|------|------|-------------|
| `PLAN.md` | Core architecture, system constraints, content-ownership rules | **Read for context. Do not edit unless the user explicitly asks.** |
| `NEXTSTEPS.md` | Active sprint queue — phased manual + code checklist | Check off items as they ship. Add new ones when the user asks. |
| `BACKLOG.md` | Quarantine for deferred ideas | Add entries when scope is cut. Move entries out when picked up. |
| `HANDOFF.md` | Session state — read first, write last | Update at end of every meaningful session. |
| `README.md` | External-facing project intro | Light edits only; not for working state. |

Cross-reference convention: when you cite a doc, use a markdown link with the path (e.g. `[PLAN.md](PLAN.md)`).

---

## Architectural hard rules

These come from `PLAN.md` and should not be violated without an explicit user override.

### Actor / writer separation

- **Notion AI is the only writer of new Task rows.** It runs as a single-document parser over Daily Briefings and Meeting Notes.
- **Hermes is the actor — it never creates Tasks.** Hermes only reads Tasks with `Status=Approved` and writes back `Status`, `System Log`, and Reflection/Briefing notes.
- The bridge from "Daily Briefing exists" → "Draft Tasks exist" is `src/notion_processor.py` (Phase 2, not yet written). This is a **standalone helper, not Hermes** — separate process, separate context.

### Storage canonicality

- **Notion** is canonical for: Tasks, current state, contacts metadata, projects, opportunities, decisions, daily briefings.
- **Obsidian** is canonical for: Skills, people intelligence, long-term memory, reflections (dual-write with Notion).
- **Sync direction is always Notion → Obsidian.** Never bidirectional.
- **Notion AI never touches Obsidian-owned content.**

### Retrieval layering (Phase 5+)

When assembling agent prompts, structure context in three disjoint blocks:

1. **NOW** — structured Notion query (open tasks, today's calendar)
2. **RECENT** — Obsidian, time-filtered (last N days of briefings/reflections)
3. **RELEVANT** — Obsidian, hybrid semantic + graph retrieval (top-K)

Memory Bank (Vertex) is not in the current architecture. Don't introduce it without a conversational surface that justifies it.

---

## Conventions

### Code

- Python `src/` layout. Internal imports use relative form: `from .module import x`.
- Type hints + `dataclass`-style config in `src/config.py`.
- Notion API calls go through `src/notion_client.py` (rate-limited to 3 req/sec).
- New external integrations: prefer direct API for **reads**, Composio for **writes** (matches the `google_clients.py` / `composio_tools.py` split).

### Secrets

- Never commit `.env`, `credentials.json`, or `token.json`. All three are in `.gitignore`.
- Before any `git add`, sanity-check `git status` — if any of those files appears, stop and fix the gitignore.
- If a secret ever lands in a commit, **revoke it immediately** before doing anything else.

### Commits

Only commit when the user explicitly asks. Match the existing style:

- Subject line: short, imperative, ends with a period.
- Optional body: one or two sentences explaining the *why*, not the *what*.
- Use a HEREDOC for the message to preserve formatting.

Example:

```bash
git commit -m "$(cat <<'EOF'
Subject line in imperative.

Optional body sentence explaining the why.
EOF
)"
```

### Plans (Cursor)

- Plan files live in `~/.cursor/plans/`, named `<slug>_<id>.plan.md`.
- Plan mode → present plan via `CreatePlan` → wait for user confirmation → switch to Agent mode → execute.
- If updating an existing plan, edit the plan markdown directly rather than calling `CreatePlan` again.
- Todos from the plan frontmatter mirror to the live `TodoWrite` tracker during execution.

### Scheduling

- `INGESTION_HOUR` and `INGESTION_MINUTE` in `.env` control the daily briefing time. They use the **Mac local clock**, not `.env` `TIMEZONE`. `TIMEZONE` only affects what "today" means inside the script.
- To change the schedule: edit `.env`, then rerun `./scripts/install_launchd.sh`.

---

## What this project deliberately is not

- Not a multi-user product. One user, one machine.
- Not a Notion clone or workflow engine. Notion is the human UI; agents are the workforce.
- Not real-time. Daily ingestion cron + minute-scale Hermes polling is the design floor.
- Not bidirectionally synced. Mirror direction is one-way (Notion → Obsidian).

---

## When in doubt

Ask one clarifying question rather than guessing. The user prefers a 30-second pause over a 30-minute wrong direction.
