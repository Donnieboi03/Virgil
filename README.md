# Virgil

A personal cognitive operating system for a Co-Founder + intern + student actively managing a high-volume professional life.

Named after Dante's guide through the underworld. Virgil captures everything, processes it into prioritized actions with human approval gates, executes routine work on your behalf, and builds a compounding memory of your professional life.

## What it does

- **Every morning at 05:00**: pulls today's calendar, unread inbox, and curated tech/politics news → writes a Daily Briefing note to Notion
- **Every morning at 05:30**: iPhone alarm fires 45 minutes before your first meeting
- **Throughout the day** (Week 2+): Hermes agent picks up approved Tasks from Notion, executes via Gmail/Calendar/Notion, and writes Reflections back
- **Over time** (Week 5+): builds a queryable Obsidian vault with people profiles, project intelligence, skill documents, and daily reflections

## Architecture

```
Hermes Agent (orchestrator)
    ↕ memory
Obsidian Vault (skills / people / projects / reflections)
    ↕ reads tasks / writes notes
Notion (human UI — 6 DBs: Notes, Tasks, Contacts, Projects, Opportunities, Decisions)
    ↕ tool calls
Composio (Gmail · Calendar · Slack) + Direct (News · Browser · Filesystem)
```

## Quickstart

### Prerequisites

- Python 3.11+
- A Notion workspace with Notion AI enabled ($10/mo)
- A Google account (Gmail + Calendar)
- See `NEXTSTEPS.md` for full account setup (~70 min)

### Week 1 setup (after completing NEXTSTEPS.md Phase 0 and Phase 1)

```bash
git clone <your-private-repo>
cd virgil

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in NOTION_TOKEN, NOTES_DB_ID, TASKS_DB_ID, TIMEZONE in .env

# First run — opens browser for Google OAuth, writes token.json
python -m src.ingestion

# Install daily cron (05:00 AM)
chmod +x scripts/install_launchd.sh
./scripts/install_launchd.sh
```

### Verify

```bash
launchctl list | grep virgil   # should show com.virgil.ingestion
```

Check your Notion Notes DB — a Daily Briefing row should be there with News, Inbox, and Schedule sections.

## Documentation

- **`PLAN.md`** — full architecture reference, all six DB schemas, 12-week build timeline, failure modes
- **`NEXTSTEPS.md`** — human-side checklist with every manual step per phase

## Build timeline

| Sprint | What ships |
|---|---|
| Week 1 (done) | Daily Briefing cron + iPhone alarm |
| Weeks 2-4 | Hermes + Composio + Gmail drafting + approval loop |
| Weeks 5-8 | Obsidian memory layer + Contacts + mirror sync |
| Weeks 9-12 | Full execution loop with DLQ, idempotency, skill refinement |

## Cost

~$30-80/month at steady state. See `PLAN.md` cost table for breakdown.

## Security

- `.env`, `credentials.json`, `token.json` are gitignored and must never be committed
- Composio holds SaaS OAuth tokens (not stored in this repo)
- Browser scope at MVP: read-only, public domains, no auth
- All external actions require human approval (Tier 2) or are drafted for review (Tier 1) unless explicitly marked Tier 0
