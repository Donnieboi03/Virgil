# Virgil — Engineering Plan

**Virgil** is a personal cognitive operating system for a Co-Founder + intern + student + active opportunity-seeker. Named after Dante's guide. It captures everything, processes it into prioritized actions, executes routine work with approval gates, and learns over time via a compounding memory substrate.

This plan is the living architecture reference. `NEXTSTEPS.md` is the human-side checklist you tick through.

---

## System overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      VIRGIL (Agentic OS)                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                Von Neumann Agent Model                      │ │
│  │                                                             │ │
│  │   ┌─────────────────┐    ┌──────────────────────────────┐  │ │
│  │   │  Hermes Agent   │◄──►│  Obsidian Vault (Memory)     │  │ │
│  │   │  (Orchestrator) │    │  skills / people / projects  │  │ │
│  │   └────────┬────────┘    │  reflections / long-mem      │  │ │
│  │            │             └──────────────────────────────┘  │ │
│  └────────────┼─────────────────────────────────────────────--┘ │
│               │                                                  │
│          writes/reads                                            │
│               ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  Notion Foundation (Human UI)               │ │
│  │                                                             │ │
│  │   Notes    Tasks    Contacts    Projects                    │ │
│  │   Opportunities     Decisions                               │ │
│  │                ▲                                            │ │
│  │           Notion AI (single-doc parser)                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                     Action Layer                            │ │
│  │                                                             │ │
│  │   Composio: Gmail · Calendar · Slack · (future SaaS)       │ │
│  │   Direct:   News RSS · Hermes Browser · Filesystem         │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘

iPhone Shortcut (05:30) ──► alarm set 45 min before first meeting
```

Three runtime processes:

| Process | Trigger | Responsibility |
|---|---|---|
| `src/ingestion.py` | Cron 05:00 daily | News + Gmail inbox + Calendar → Notion Daily Briefing |
| `src/executor.py` (Week 2+) | Hermes daemon, polls 1-5 min | Task execution loop |
| `src/mirror_sync.py` (Week 5+) | Cron every 15 min | Notion → Obsidian one-way archive |

---

## Layer descriptions

### Hermes Agent (CPU)
Open-source agent framework by Nous Research (MIT, released Feb 2026). Provides:
- Persistent skill documents (GEPA self-improvement loop)
- Native cron scheduler (replaces launchd for Week 2+ jobs)
- MCP consumption (reads Obsidian semantic memory MCP, Composio MCP)
- Multi-platform messaging gateway (Telegram, Slack, Discord — optional)
- Parallel sub-agent execution

Runtime: local laptop or VPS. Abstract behind `src/agent_runtime.py` (Week 2) so the location is swappable without changing calling code.

Version pin: always pin explicitly in `requirements.txt`. API changes in minor versions of a 3-month-old framework are common.

### Obsidian Vault (Memory)
Local-first vault. Agent writes here; user reads here optionally. Never synced back to Notion.

```
virgil-vault/
├── _archive/notion/          # one-way mirror from Notion (read-only, sync process writes)
├── skills/                   # Hermes-managed reusable procedure documents (agentskills.io)
├── people/                   # one .md per Contact, agent-maintained
├── projects/                 # one .md per Project, agent-maintained
├── opportunities/            # one .md per Opportunity, agent-maintained
├── decisions/                # mirror from Notion Decisions DB, enriched by Hermes
├── reflections/              # per-task + daily reflections, dual-written
└── meta/                     # vault config, MCP server config, agent state
```

obsidian-semantic-memory MCP server runs over the whole vault, exposing hybrid semantic + BM25 + graph search to Hermes.

### Notion Foundation (Human UI)
The cockpit. You read and approve here. Notion AI parses single documents into structured outputs. Hermes reads Tasks and writes Notes/Reflections here.

Six databases (see schemas in Section 4).

**Hard rule:** Notion AI owns initial single-doc extraction. Hermes owns cross-document reasoning, deduplication, state transitions, and memory enrichment.

### Composio (OAuth Vault)
Holds OAuth tokens for all SaaS integrations so Virgil never manages token refresh. Exposes actions as MCP tools that Hermes consumes.

Use Composio for: Gmail, Google Calendar, Slack, Linear, and any future SaaS with OAuth.
Use direct APIs for: News RSS (API key or keyless), Browser (Hermes native), Filesystem.

### Action Layer
Browser scope at MVP: **read-only on public news/research domains. No auth flows, no form submission, no logged-in sessions.** Expand scope only after explicit decision in a future sprint.

---

## The Execution Loop

```
1. INGESTION  (cron 05:00)
   Sources: Gmail unread last 24h, Google Calendar today, RSS news feeds
   Output:  Notion Notes row, Kind=Daily Briefing
   Code:    src/ingestion.py

2. PROCESSING  (Notion AI, on note creation)
   Input:   Any new Note
   Output:  Draft Tasks (Status=Draft), extracted Contact candidates
   Who:     Notion AI (single-doc)

3. APPROVAL GATE  (human, async)
   Tier 0   → auto-approved immediately
   Tier 1   → drafted (Gmail Drafts / Calendar tentative), human sends/confirms
   Tier 2   → Status=Pending Approval, human taps Approve per-row or batch
   Tier 3   → agent never executes; writes research note only

4. EXECUTION  (Hermes daemon, polls 1-5 min)
   - Check WIP capacity (max N in Processing, configurable)
   - Check DLQ depth (throttle if > 20 open failures)
   - Pull next Approved task sorted by Eisenhower quadrant
   - Write External Action ID to row (idempotency anchor)
   - Set Status=Processing
   - Execute via Composio MCP / direct API / Hermes browser
   - On success → Status=Executed, write Reflection, update Contact, refine Skill
   - On transient failure → requeue, retry_count++ (max 3 attempts)
   - On other failure → Status=Failed, set Failure Category, surface in DLQ view

5. DLQ REVIEW  (human, weekly + on-demand)
   DLQ = saved filter view on Tasks DB (Status=Failed)
   Grouped by Failure Category
   Per-row buttons: Retry / Clarify / Approve+Retry / Reformulate / Drop

6. LEARNING  (Hermes, weekly cron)
   - Cluster successes → refine Skills in Obsidian
   - Cluster failures → propose new Skills or missing data sources
   - Write "Weekly System Reflection" note
```

### Failure taxonomy

| Category | Examples | Handling |
|---|---|---|
| Transient | Gmail 503, rate limit, timeout | Auto-retry, exponential backoff, max 3 |
| Missing Context | "Email Sarah" but no email on file | DLQ immediately, Failure Category = Missing Context |
| Refused / Safety | Tier 3 task, agent self-declined | DLQ as "needs explicit approval" |
| Hard Error | Malformed task, contradictory instructions | DLQ as "needs reformulation" — retry guaranteed to fail |

Only Transient retries automatically. The others go to DLQ immediately.

### Idempotency

Every external action gets an `External Action ID` written to the Task row *before* execution. On any retry, Hermes checks whether the ID was already applied successfully before re-executing. Prevents duplicate sends.

---

## Approval tiers

| Tier | Label | Examples | Pattern |
|---|---|---|---|
| 0 | Auto | Read inbox, write Reflection, update Obsidian, set Notion status | No approval |
| 1 | Draft | Compose email, propose calendar event | Gmail Drafts / Calendar tentative — you send/confirm |
| 2 | Approval | Send email, book confirmed meeting, post to Slack | Status=Pending Approval; Approve button per-row or batch view |
| 3 | Manual | Sign anything, pay anything, legally irreversible | Agent never executes; writes research note with options |

Notion AI assigns initial tier on Task creation (defaults to Tier 2 when uncertain). User can override on review.

---

## Content drift ownership

Bidirectional sync is never used. Mirror direction is always Notion → Obsidian (one-way).

| Content kind | Canonical store | Writer(s) | Mirror to Obsidian? |
|---|---|---|---|
| Meeting Notes | Notion | Notion AI | Yes — archive copy |
| Daily Briefings | Notion | Hermes (ingestion.py) | Yes — archive copy |
| Tasks | Notion | Notion AI creates, Hermes sets status only | No (Hermes reads via API) |
| Contacts (metadata) | Notion | Notion AI extracts, Hermes enriches | Yes — enriched .md per person |
| Projects | Notion | Human creates | Yes — Hermes adds intelligence layer |
| Opportunities | Notion | Human or Notion AI | Yes — Hermes adds pipeline context |
| Decisions | Notion | Human | Yes — mirror copy |
| **Skills** | **Obsidian only** | Hermes (GEPA) | Never to Notion |
| **People intelligence** | **Obsidian only** | Hermes | Never to Notion |
| **Long-term memory** | **Obsidian only** | Hermes | Never to Notion |
| Reflections | Both (dual-write, immutable) | Hermes | Written to both simultaneously |

Notion AI never touches Obsidian-owned content. Hermes never edits Notion content except:
- Task `Status` fields (state transitions only)
- `System Log` on Tasks
- `Last Interaction` + `Context Summary` on Contacts
- Creating new Notes rows (Reflections, Daily Briefings)

---

## Notion database schemas

### 1. Notes

One database for all written context. `Kind` field distinguishes types.

| Property | Type | Notes |
|---|---|---|
| `Title` | Title | Auto-generated by Notion AI or Hermes |
| `Kind` | Select | Daily Briefing / Meeting Notes / Task Reflection / Weekly Reflection |
| `Date` | Date | |
| `Body` | (page body) | Full content lives in page body, not a column |
| `Project` | Relation → Projects | |
| `Opportunity` | Relation → Opportunities | Optional |
| `Contacts` | Relation → Contacts | Multi |
| `Created` | Created time | Auto |

### 2. Tasks

| Property | Type | Notes |
|---|---|---|
| `Task Name` | Title | |
| `Context` | Text | Natural-language instruction for the agent |
| `Target` | Select | Gmail / Calendar / Notion / Browser / Manual |
| `Risk Tier` | Select | 0-Auto / 1-Draft / 2-Approval / 3-Manual |
| `Status` | Select | Draft / Approved / Processing / Executed / Failed / DLQ-Resolved |
| `Eisenhower` | Select | Q1 Urgent+Important / Q2 Important / Q3 Urgent / Q4 Neither |
| `WIP Slot` | Number | Counts against concurrency limit when in Processing |
| `External Action ID` | Text | Idempotency key, written before execution |
| `Failure Category` | Select | Transient / Missing Context / Refused / Hard Error / None |
| `Failure Reason` | Text | What Hermes observed |
| `Retry Count` | Number | |
| `First Failed At` | Date | |
| `Last Failed At` | Date | |
| `Resolution Action` | Select | Retry / Clarify / Approve+Retry / Reformulate / Drop |
| `System Log` | Text | Written back by executor |
| `Project` | Relation → Projects | |
| `Opportunity` | Relation → Opportunities | |
| `Contacts` | Relation → Contacts | Multi |
| `Created` | Created time | Auto |

**DLQ view** = saved filter on Tasks where `Status = Failed`, grouped by `Failure Category`. One-tap resolution buttons per row.

**Approve batch view** = saved filter where `Status = Pending Approval`, sorted by `Eisenhower`.

### 3. Contacts

| Property | Type | Notes |
|---|---|---|
| `Name` | Title | |
| `Email` | Email | Primary key for dedup by Hermes |
| `Company` | Text | Promote to Companies DB later if needed |
| `Role` | Text | |
| `Relationship` | Select | Investor / Co-founder / Advisor / Recruiter / Professor / Classmate / Customer / Other |
| `First Met` | Date | |
| `Last Interaction` | Date | Auto-updated by Hermes after each execution touching this contact |
| `Context Summary` | Text | Maintained by Hermes; what to remember about this person |
| `Status` | Select | Active / Warm / Cold / Dormant |
| `Next Follow-up` | Date | Hermes suggests; human approves |
| `Tasks` | Relation → Tasks | |
| `Notes` | Relation → Notes | |
| `Opportunities` | Relation → Opportunities | |
| `Decisions` | Relation → Decisions | |
| `Created` | Created time | Auto |

Contact dedup rule: Notion AI creates candidate Contacts. Hermes runs a daily reconciliation pass, merging candidates against existing entries by email → company → name match. Ambiguous merges surface as Tasks for human review.

### 4. Projects

| Property | Type | Notes |
|---|---|---|
| `Name` | Title | |
| `Description` | Text | |
| `Status` | Select | Active / Paused / Complete |
| `Kind` | Select | Startup / Internship / Academic / Personal |
| `Tasks` | Relation → Tasks | |
| `Notes` | Relation → Notes | |
| `Opportunities` | Relation → Opportunities | |
| `Decisions` | Relation → Decisions | |
| `Contacts` | Relation → Contacts | |

### 5. Opportunities

Tracks specific pipeline items with defined outcomes. Separate from Projects (which are ongoing).

| Property | Type | Notes |
|---|---|---|
| `Name` | Title | |
| `Kind` | Select | Job / Grant / Partnership / Investment / Other |
| `Organization` | Text | |
| `Stage` | Select | Prospect / Engaged / Active / Decision / Closed-Won / Closed-Lost |
| `Deadline` | Date | |
| `Next Action` | Date | |
| `Notes` | Relation → Notes | |
| `Tasks` | Relation → Tasks | |
| `Contacts` | Relation → Contacts | Key people involved |
| `Project` | Relation → Projects | Parent context |
| `Decisions` | Relation → Decisions | |

### 6. Decisions

Founder-grade decision log. Captures the reasoning at decision time and the actual outcome retrospectively.

| Property | Type | Notes |
|---|---|---|
| `Decision` | Title | |
| `Date` | Date | |
| `Alternatives Considered` | Text | |
| `Reasoning` | Text | Why this choice |
| `Predicted Outcome` | Text | What you expected to happen |
| `Actual Outcome` | Text | Filled in retrospectively |
| `Lesson` | Text | Filled in retrospectively |
| `Project` | Relation → Projects | |
| `Opportunity` | Relation → Opportunities | Optional |
| `Contacts` | Relation → Contacts | Who was involved |

Notion AI prompts retrospective fills monthly via a cron-triggered Task.

---

## Notion AI responsibilities

Notion AI is the single-document parser. It never touches cross-document reasoning or state machines.

| Trigger | Notion AI action |
|---|---|
| New Meeting Notes page | Extract action items as Draft Tasks, extract Contact candidates |
| New Daily Briefing | Summarize into task suggestions for any time-sensitive items |
| New Opportunity created | Suggest next-action Task |
| Monthly cron Task | Prompt decision retrospective fills on Decisions with empty Actual Outcome |

Hermes does: cross-document dedup, Contact enrichment, Task state transitions, Obsidian writes, skill refinement, DLQ management.

---

## Tool layer

| Capability | Provider | Notes |
|---|---|---|
| Gmail send/draft/reply/fetch | Composio | MCP tool `GMAIL_SEND_EMAIL`, `GMAIL_REPLY_TO_THREAD`, `GMAIL_FETCH_EMAILS` |
| Google Calendar | Composio | `GOOGLECALENDAR_CREATE_EVENT`, `GOOGLECALENDAR_UPDATE_EVENT` |
| Notion reads/writes | Composio or notion-client | Pick one; notion-client used in ingestion.py for simplicity, Composio MCP used by Hermes |
| Slack (future) | Composio | Add when needed |
| News RSS | Direct — feedparser | No OAuth, env-driven feed list |
| Browser | Hermes native | Read-only, public domains, no auth at MVP |
| Filesystem / Obsidian | Hermes native | Local vault path |
| Semantic memory | obsidian-semantic-memory MCP | Hybrid semantic + BM25 + graph search over vault |

---

## 12-week build timeline

### Week 1 — Vertical Slice (shipped this sprint)

**Goal**: morning briefing + meeting alarm working. Solves oversleeping and triage time from day 3.

- [x] `src/config.py` — env loading, validation, typed config
- [x] `src/notion_client.py` — Notion wrapper with rate limiting
- [x] `src/google_clients.py` — Gmail + Calendar, read-only OAuth
- [x] `src/news.py` — RSS aggregator
- [x] `src/ingestion.py` — Daily Briefing entrypoint
- [x] `scripts/install_launchd.sh` — 05:00 daily cron
- [ ] **Manual**: create Notion DBs (Notes + Tasks at minimum), Notion integration token
- [ ] **Manual**: Google Cloud project + `credentials.json`
- [ ] **Manual**: populate `.env` and run first-time OAuth
- [ ] **Manual**: iPhone Shortcut (05:30 alarm, 45 min before first meeting)

**Outcome**: Daily Briefing lands in Notion at 05:00. Phone alarm wakes you before meetings.

---

### Weeks 2-4 — Action Layer

**Goal**: agent can draft emails, you approve, it sends.

- [ ] Composio account + Gmail / Calendar / Notion integrations connected
- [ ] OpenRouter account + API key
- [ ] Hermes installed, configured with OpenRouter as LLM provider
- [ ] `src/agent_runtime.py` — thin Hermes wrapper (runtime location–agnostic)
- [ ] `src/executor.py` — Hermes daemon: poll Tasks, WIP check, execute, reflect
- [ ] `src/prompts.py` — executor system prompt + transcript parser prompt
- [ ] `src/composio_tools.py` — toolset loader filtered by Target field
- [ ] Notion Tasks DB extended schema (Risk Tier, Eisenhower, External Action ID, Failure fields)
- [ ] Approval tier logic: Tier 1 → Gmail Drafts; Tier 2 → Pending Approval status
- [ ] Reflection writes back to Notes DB
- [ ] launchd plist for executor daemon (or Hermes native scheduler)
- [ ] Phase 2 smoke test: one Task executed end-to-end, Reflection written

**Outcome**: "Draft reply to this email" works. WIP-gated, idempotent.

---

### Weeks 5-8 — Memory Layer

**Goal**: agent has persistent memory; email drafts use contact context.

- [ ] Obsidian vault scaffolded (`virgil-vault/` directory structure)
- [ ] `obsidian-semantic-memory` MCP server configured over vault
- [ ] `src/mirror_sync.py` — Notion → Obsidian one-way archive (cron 15 min)
- [ ] Notion Contacts DB created with full schema + relations
- [ ] Notion Projects DB created with relations
- [ ] Hermes injects related Obsidian context into every LLM call (people profiles, project notes)
- [ ] Contact dedup: Hermes daily reconciliation job
- [ ] One-time backfill: extract historical contacts from Gmail into Obsidian + Notion
- [ ] Notion → Obsidian rate limiter (3 req/sec token bucket, shared across all processes)

**Outcome**: agent knows who you're talking to. Drafts use accumulated context.

---

### Weeks 9-12 — Full Loop + Learning

**Goal**: self-improving system with DLQ, idempotency, skill refinement.

- [ ] Notion Opportunities DB created with pipeline stages + relations
- [ ] Notion Decisions DB created with retrospective fields + relations
- [ ] DLQ view on Tasks DB (saved filter + Failure Category grouping)
- [ ] Per-row DLQ resolution buttons (Retry / Clarify / Approve+Retry / Reformulate / Drop)
- [ ] Failure taxonomy in executor: 4 categories, different retry behavior
- [ ] External Action ID idempotency enforced on all Composio calls
- [ ] Weekly Hermes skill-refinement cron (clusters successes + failures → refines/proposes Skills)
- [ ] Weekly System Reflection note generated
- [ ] Skill Gap surfacing (agent proposes new skills based on DLQ patterns)
- [ ] Opportunity pipeline follow-up Tasks generated by Hermes (stale stage detection)
- [ ] Decision retrospective prompt cron (monthly)
- [ ] DLQ depth monitoring: throttle ingestion when > 20 open failures

**Outcome**: full execution loop with learning. System self-improves and manages its own failure modes.

---

### Month 4+ — Hardening and Expansion

- iPhone alarm pipeline: already delivered in Week 1; revisit only if runtime changes
- VPS migration for Hermes daemon (if laptop sleep is causing missed polls)
- Composio tier upgrade if volume demands it
- Browser scope expansion (controlled, behind explicit approval)
- Additional SaaS integrations (Slack, Linear) via Composio
- Companies DB (promote from Text field on Contacts when query patterns demand it)
- Hermes multi-platform messaging (Telegram or Slack personal bot for approvals on the go)

---

## Repository layout

```
virgil/
├── PLAN.md                         # this file
├── NEXTSTEPS.md                    # human-side manual checklist
├── README.md
├── .gitignore
├── .env                            # gitignored, populated from .env.example
├── .env.example
├── requirements.txt                # grows per sprint
├── credentials.json                # gitignored, Google OAuth client
├── token.json                      # gitignored, generated on first run
├── src/
│   ├── __init__.py
│   ├── config.py                   # env loading + validation (Week 1)
│   ├── notion_client.py            # Notion wrapper (Week 1)
│   ├── google_clients.py           # Gmail + Calendar (Week 1)
│   ├── news.py                     # RSS aggregator (Week 1)
│   ├── ingestion.py                # Daily Briefing entrypoint (Week 1)
│   ├── agent_runtime.py            # Hermes wrapper (Week 2)
│   ├── executor.py                 # Task execution daemon (Week 2)
│   ├── prompts.py                  # LLM system prompts (Week 2)
│   ├── composio_tools.py           # Composio toolset loader (Week 2)
│   └── mirror_sync.py              # Notion → Obsidian sync (Week 5)
├── scripts/
│   ├── install_launchd.sh          # macOS launchd installer
│   └── com.virgil.ingestion.plist  # launchd plist template
├── obsidian/                       # symlink or path to virgil-vault/
│   └── .gitkeep
└── logs/
    └── .gitkeep
```

---

## Cost at steady state

| Service | Cost/month | Required from |
|---|---|---|
| Notion AI | $10 | Week 2 |
| Composio | $0-20 | Week 2 (free tier likely sufficient solo) |
| OpenRouter (LLM) | $20-40 | Week 2 |
| Obsidian | $0 | Week 5 (Obsidian Sync $5 optional) |
| Hermes | $0 | Week 2 (open source) |
| VPS (optional) | $5-10 | Month 2+ if laptop sleeps overnight |
| **Total** | **$30-80** | |

---

## Open decisions (decide before relevant sprint)

| Decision | Must decide by | Options | Current default |
|---|---|---|---|
| Hermes run location | Week 2 | Laptop launchd / VPS | Laptop for weeks 2-4, VPS before week 8 |
| Obsidian Sync | Week 5 | Local only / Obsidian Sync $5 / iCloud | Local only at MVP |
| Notion API access method for Hermes | Week 2 | notion-client direct / Composio MCP | Composio MCP (consistent with tool layer) |
| Contact dedup confidence threshold | Week 5 | High (manual review always) / Low (Hermes merges if email matches) | High — surface ambiguous merges as Tasks |
| Weekly skill refinement model | Week 9 | Same as execution model / smarter model for reasoning | Same model (OpenRouter) |

---

## Failure modes and remediation

| Symptom | Root cause | Fix |
|---|---|---|
| Notion API 404 on DB ID | DB not shared with integration | NEXTSTEPS.md Phase 0, step 4 |
| OAuth flow opens browser on every cron run | `token.json` not writable or missing | `chmod 600 token.json`, check Full Disk Access |
| Task stuck in Processing | Executor crashed mid-loop | Check `logs/executor.err`, restart daemon |
| Email sent twice | External Action ID not written before execution | Enforce ID write in executor before any Composio call |
| Composio 400 Unauthorized | OAuth token expired in Composio | Reconnect integration in Composio dashboard |
| Duplicate Contacts | Notion AI extracted same person from two meeting notes | Run Hermes dedup job manually; add email to both entries first |
| DLQ growing unchecked | Executor failing silently | Check `logs/executor.err`; review DLQ view |
| Apple alarm never fires | Shortcut set to "Ask Before Running" | Toggle to "Run Immediately" in Shortcuts app |
| Notion rate limit 429 | Multiple processes hitting Notion simultaneously | Shared token-bucket rate limiter in `notion_client.py` enforces 3 req/sec |
| Content drift: Notion AI rewrites a Task title Hermes references | Task ID reference broken | Hermes always references Task by Notion page ID, never by display title |
