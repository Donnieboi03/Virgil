# Virgil — Manual Setup Checklist

This file is your personal to-do list. Everything here is a step only *you* can complete — it requires clicking through UIs, authorizing accounts, or running a one-time command on your machine. The code is already written; this bridges the gap.

Work through phases in order. Do not start Phase 1 before Phase 0 is done.

Estimated total time: **~70 minutes** spread across whenever you have access to each service.

---

## Current progress

_Last updated: 2026-05-21_

- [x] **Phase 0 — Notion** (Notes + Tasks only; Contacts/Projects/Opportunities/Decisions deferred per their `(can defer …)` labels)
- [ ] **Phase 1 — Google Cloud** ← you are here
- [ ] Phase 2 — Composio + OpenRouter + Hermes (Week 2)
- [ ] Phase 3 — iPhone Shortcut (anytime after Phase 1)

The four deferred DBs (Contacts, Projects, Opportunities, Decisions) are not required for Week 1. When you create them, come back and fill in the matching `*_DB_ID` rows in `.env`, share each with the `Virgil Agent` integration, and tick the boxes in Phase 0 Steps 2 and 4.

---

## Phase 0 — Notion (30 min)

### Step 1: Create the six databases

In your Notion workspace, create six new full-page databases. For each:
- Click **New page** in the sidebar
- Choose **Table** (full page)
- Name it exactly as shown
- Delete default rows
- Add properties per the schemas below

**Use the exact property names listed** — the code references them by name.

Status:
- [x] Notes — created
- [x] Tasks — created
- [ ] Contacts *(deferred to Week 2-3)*
- [ ] Projects *(deferred to Week 2-3)*
- [ ] Opportunities *(deferred to Week 9-12)*
- [ ] Decisions *(deferred to Week 9-12)*

---

#### Database 1: Notes

| Property | Type |
|---|---|
| `Title` | Title (rename the default "Name" column) |
| `Kind` | Select — add options: `Daily Briefing`, `Meeting Notes`, `Task Reflection`, `Weekly Reflection` |
| `Date` | Date |
| `Project` | Relation → Projects *(add after Projects DB exists)* |
| `Opportunity` | Relation → Opportunities *(add after Opportunities DB exists)* |
| `Contacts` | Relation → Contacts *(add after Contacts DB exists)* |

---

#### Database 2: Tasks

| Property | Type |
|---|---|
| `Task Name` | Title (rename the default column) |
| `Context` | Text |
| `Target` | Select — options: `Gmail`, `Calendar`, `Notion`, `Browser`, `Manual` |
| `Risk Tier` | Select — options: `0-Auto`, `1-Draft`, `2-Approval`, `3-Manual` |
| `Status` | Select — options: `Draft`, `Approved`, `Processing`, `Executed`, `Failed`, `DLQ-Resolved` |
| `Eisenhower` | Select — options: `Q1 Urgent+Important`, `Q2 Important`, `Q3 Urgent`, `Q4 Neither` |
| `WIP Slot` | Number |
| `External Action ID` | Text |
| `Failure Category` | Select — options: `Transient`, `Missing Context`, `Refused`, `Hard Error`, `None` |
| `Failure Reason` | Text |
| `Retry Count` | Number |
| `First Failed At` | Date |
| `Last Failed At` | Date |
| `Resolution Action` | Select — options: `Retry`, `Clarify`, `Approve+Retry`, `Reformulate`, `Drop` |
| `System Log` | Text |
| `Project` | Relation → Projects *(add after Projects DB exists)* |
| `Opportunity` | Relation → Opportunities *(add after Opportunities DB exists)* |
| `Contacts` | Relation → Contacts *(add after Contacts DB exists)* |

**After creating Tasks:** add two saved views:

- **DLQ view**: filter `Status = Failed`, group by `Failure Category`, name it "DLQ"
- **Approve queue**: filter `Status = Approved`, sort by `Eisenhower` ascending, name it "Approve Queue"

---

#### Database 3: Contacts *(can defer to Week 2-3)*

| Property | Type |
|---|---|
| `Name` | Title |
| `Email` | Email |
| `Company` | Text |
| `Role` | Text |
| `Relationship` | Select — options: `Investor`, `Co-founder`, `Advisor`, `Recruiter`, `Professor`, `Classmate`, `Customer`, `Other` |
| `First Met` | Date |
| `Last Interaction` | Date |
| `Context Summary` | Text |
| `Status` | Select — options: `Active`, `Warm`, `Cold`, `Dormant` |
| `Next Follow-up` | Date |
| `Tasks` | Relation → Tasks |
| `Notes` | Relation → Notes |
| `Opportunities` | Relation → Opportunities *(add after Opportunities DB exists)* |
| `Decisions` | Relation → Decisions *(add after Decisions DB exists)* |

---

#### Database 4: Projects *(can defer to Week 2-3)*

| Property | Type |
|---|---|
| `Name` | Title |
| `Description` | Text |
| `Status` | Select — options: `Active`, `Paused`, `Complete` |
| `Kind` | Select — options: `Startup`, `Internship`, `Academic`, `Personal` |
| `Tasks` | Relation → Tasks |
| `Notes` | Relation → Notes |
| `Opportunities` | Relation → Opportunities *(add after Opportunities DB exists)* |
| `Decisions` | Relation → Decisions *(add after Decisions DB exists)* |
| `Contacts` | Relation → Contacts |

**After creating:** add your real projects as rows (your startup, your internship, any academic projects).

---

#### Database 5: Opportunities *(defer to Week 9-12)*

| Property | Type |
|---|---|
| `Name` | Title |
| `Kind` | Select — options: `Job`, `Grant`, `Partnership`, `Investment`, `Other` |
| `Organization` | Text |
| `Stage` | Select — options: `Prospect`, `Engaged`, `Active`, `Decision`, `Closed-Won`, `Closed-Lost` |
| `Deadline` | Date |
| `Next Action` | Date |
| `Notes` | Relation → Notes |
| `Tasks` | Relation → Tasks |
| `Contacts` | Relation → Contacts |
| `Project` | Relation → Projects |
| `Decisions` | Relation → Decisions |

---

#### Database 6: Decisions *(defer to Week 9-12)*

| Property | Type |
|---|---|
| `Decision` | Title |
| `Date` | Date |
| `Alternatives Considered` | Text |
| `Reasoning` | Text |
| `Predicted Outcome` | Text |
| `Actual Outcome` | Text |
| `Lesson` | Text |
| `Project` | Relation → Projects |
| `Opportunity` | Relation → Opportunities |
| `Contacts` | Relation → Contacts |

---

### Step 2: Get the database IDs

For **Notes** and **Tasks** (the two you need for Week 1):

1. Open the database
2. Click **Share** (top right) → **Copy link**
3. The URL looks like: `https://www.notion.so/your-workspace/Title-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX?v=...`
4. The 32-character hex string **before** the `?` is the database ID
5. Format it with dashes: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (Notion accepts both formats)

Save these — you'll put them in `.env` in Phase 1, Step 2.

- [x] `NOTES_DB_ID` — set in `.env`
- [x] `TASKS_DB_ID` — set in `.env`
- [ ] `CONTACTS_DB_ID` *(fill when you create it)*
- [ ] `PROJECTS_DB_ID` *(fill when you create it)*
- [ ] `OPPORTUNITIES_DB_ID` *(fill when you create it)*
- [ ] `DECISIONS_DB_ID` *(fill when you create it)*

---

### Step 3: Create the Notion integration

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **+ New integration**
3. Name it `Virgil Agent`
4. Select your workspace
5. Under **Capabilities**: check `Read content`, `Update content`, `Insert content`
6. Click **Submit**
7. Copy the **Internal Integration Secret** (starts with `secret_`)

Save it — this becomes `NOTION_TOKEN` in your `.env`.

- [x] `NOTION_TOKEN` — set in `.env`

---

### Step 4: Share databases with the integration

For every database you've created:
1. Open the database
2. Click `...` (top right) → **Add connections**
3. Search for `Virgil Agent` and select it

**If you skip this step, every API call returns 404. It must be done for every DB.**

- [x] Notes shared with Virgil Agent
- [x] Tasks shared with Virgil Agent
- [ ] Contacts shared with Virgil Agent *(when created)*
- [ ] Projects shared with Virgil Agent *(when created)*
- [ ] Opportunities shared with Virgil Agent *(when created)*
- [ ] Decisions shared with Virgil Agent *(when created)*

---

### Step 5: Enable Notion AI *(needed by Week 2)*

Go to **Settings → Plans** in your Notion workspace and enable Notion AI ($10/month). Not needed for Week 1 (the ingestion script writes directly via API), but required before the Week 2 sprint.

- [ ] Notion AI enabled

---

### Phase 0 complete check

Run this in your terminal once `.env` has `NOTION_TOKEN`, `NOTES_DB_ID`, and `TASKS_DB_ID` filled in. No virtualenv needed — only `curl` and the system `python3`.

```bash
cd /Users/donnieb/Desktop/Code/Virgil
set -a && source .env && set +a   # load NOTION_TOKEN + *_DB_ID into the shell

curl -s "https://api.notion.com/v1/databases/$NOTES_DB_ID" \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Notion-Version: 2022-06-28" | python3 -m json.tool | grep '"plain_text"'

curl -s "https://api.notion.com/v1/databases/$TASKS_DB_ID" \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Notion-Version: 2022-06-28" | python3 -m json.tool | grep '"plain_text"'
```

You should see `"plain_text": "Notes"` from the first call and `"plain_text": "Tasks"` from the second.

If `grep` prints nothing, rerun the same `curl | python3 -m json.tool` without the `grep` and look at the response:
- `"object": "database"` + a `title` block → success (grep just didn't find the title token).
- `"status": 401` / `"unauthorized"` → bad `NOTION_TOKEN`.
- `"status": 404` / `"object_not_found"` → DB ID is wrong, or the `Virgil Agent` integration isn't connected to that database (open the DB → `⋯` top right → **Connections** → add it).

Status:
- [x] Notes DB returns `"object": "database"`
- [x] Tasks DB returns `"object": "database"`

---

## Phase 1 — Google Cloud (15 min)

### Step 1: Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown (top left) → **New Project**
3. Name it `virgil-ingestion`, click **Create**
4. **APIs & Services → Library** → search and enable:
   - `Gmail API`
   - `Google Calendar API`
5. **OAuth consent screen** → External → fill required fields:
   - App name: `Virgil`
   - User support email: your Gmail
   - Developer contact email: your Gmail
   - Click **Save and Continue** through all steps (no scopes needed in the form)
6. Under **Test users** → Add your own Gmail address

---

### Step 2: Create OAuth credentials

1. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
2. Application type: **Desktop app**
3. Name: `Virgil Desktop`
4. Click **Create**
5. Download the JSON file
6. Rename it to `credentials.json`
7. Move it to `/Users/donnieb/Desktop/Code/Virgil/credentials.json`

---

### Step 3: Populate `.env`

Open the `.env.example` file and copy it to `.env`:

```bash
cd /Users/donnieb/Desktop/Code/Virgil
cp .env.example .env
```

Fill in every value that has a placeholder:

```
NOTION_TOKEN=secret_...            ← from Phase 0 Step 3
NOTES_DB_ID=...                    ← from Phase 0 Step 2
TASKS_DB_ID=...                    ← from Phase 0 Step 2
TIMEZONE=America/Los_Angeles       ← or your timezone
NEWS_RSS_FEEDS=...                 ← defaults are pre-filled; edit if desired
```

Leave `COMPOSIO_API_KEY` and `OPENROUTER_API_KEY` blank for now — those are Week 2.

> **Heads up:** `.env.example` ships with `OBSIDIAN_VAULT_PATH=/Users/donnieb/Desktop/Code/Vigil/obsidian` (typo). When you copy it, edit your `.env` to use the correct `…/Virgil/obsidian` path. Not required for Week 1, but easier to fix now than later.

Status:
- [x] `NOTION_TOKEN`, `NOTES_DB_ID`, `TASKS_DB_ID` filled
- [ ] `TIMEZONE` confirmed
- [ ] `OBSIDIAN_VAULT_PATH` corrected to `…/Virgil/obsidian`

---

### Step 4: Create the virtualenv and install dependencies

```bash
cd /Users/donnieb/Desktop/Code/Virgil
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Sanity check that the core packages installed:

```bash
python -c "import notion_client, google.auth, googleapiclient, feedparser; print('deps OK')"
```

---

### Step 5: Run first-time OAuth

```bash
source .venv/bin/activate
python -m src.ingestion
```

A browser window will open asking you to log into your Google account. Click **Allow**. This writes `token.json` to the repo root. The script will then complete its first run and write a Daily Briefing note to Notion.

**macOS note:** If the briefing note appears but later cron runs fail silently, you need to grant Full Disk Access to `cron`:
- System Settings → Privacy & Security → Full Disk Access → click `+` → navigate to `/usr/sbin/cron`

- [ ] `token.json` created
- [ ] Daily Briefing note appeared in Notion Notes DB
- [ ] News, Inbox, and Schedule sections are populated

---

### Step 6: Install the daily cron

```bash
chmod +x scripts/install_launchd.sh
./scripts/install_launchd.sh
```

Verify it loaded:

```bash
launchctl list | grep virgil
```

Should show `com.virgil.ingestion`. The briefing will now run automatically at 05:00 every morning.

- [ ] launchd job installed
- [ ] Verified with `launchctl list | grep virgil`

---

## Phase 2 — Composio + OpenRouter + Hermes *(Week 2, do before starting Week 2 sprint)*

### Step 1: Create Composio account

1. Go to [app.composio.dev](https://app.composio.dev) and sign up
2. **Integrations** tab → connect:
   - **Gmail** — authorize with your Google account
   - **Google Calendar** — authorize with your Google account
   - **Notion** — authorize with your Notion account
3. **Settings → API Keys** → create a key → copy it

Save it as `COMPOSIO_API_KEY` in your `.env`.

- [ ] Composio account created
- [ ] Gmail connected
- [ ] Google Calendar connected
- [ ] Notion connected
- [ ] API key saved to `.env`

---

### Step 2: Create OpenRouter account

1. Go to [openrouter.ai](https://openrouter.ai) and sign up
2. **Keys** → Create a new API key → copy it
3. Add $10-20 in credits to start (pay-as-you-go)

Save it as `OPENROUTER_API_KEY` in your `.env`.

- [ ] OpenRouter account created
- [ ] API key saved to `.env`
- [ ] Credits loaded

---

### Step 3: Install Hermes Agent

```bash
source .venv/bin/activate
pip install hermes-agent
hermes login    # follow CLI prompts
```

Configure Hermes to use OpenRouter (exact config syntax is in the Week 2 sprint plan when it runs).

- [ ] Hermes installed
- [ ] Hermes CLI authenticated

---

## Phase 3 — iPhone Shortcut *(can be done any time after Phase 1)*

This shortcut fires at 05:30 every morning and creates an alarm 45 minutes before your first calendar event for the day.

### Step 1: Confirm Google Calendar is synced to iPhone

1. **Settings → Calendar → Accounts → Add Account → Google**
2. Sign in. Toggle **Calendars: ON**.
3. **Settings → Calendar → Accounts → Fetch New Data** → set the Google account to **Push** (or Every 15 Minutes if Push isn't available).

- [ ] Google Calendar synced to iPhone

---

### Step 2: Build the Shortcut

Open the **Shortcuts** app → **Automation** tab → `+` → **Create Personal Automation**

1. Trigger: **Time of Day** → `05:30 AM` → **Daily** → toggle **Run Immediately** ON (not "Ask Before Running")

2. Add these actions in order:

   **Action 1 — Find Calendar Events**
   - Action: `Find Calendar Events`
   - Filter: `Start Date` is `Today`
   - Calendar: your primary Google Calendar
   - Sort: by `Start Date` ascending
   - Limit: `1`

   **Action 2 — Check if any events found**
   - Action: `If`
   - Input: `Count` of the result from Action 1
   - Condition: `is less than` `1`
   - Then: `Stop Shortcut`

   **Action 3 — Get Start Date**
   - Action: `Get Details of Calendar Events`
   - Detail: `Start Date`
   - From: the result of Action 1

   **Action 4 — Adjust Date**
   - Action: `Adjust Date`
   - Add/Subtract: **Subtract** `45` **Minutes**
   - From: result of Action 3

   **Action 5 — Create Alarm**
   - Action: `Set Alarm`
   - Time: result of Action 4
   - Label: `Meeting Prep`
   - Enabled: yes

3. Tap **Done**

- [ ] Shortcut created with Run Immediately ON
- [ ] Test: create a calendar event tomorrow at 09:00. By 05:30 tomorrow, an alarm should appear in Clock set for 08:15.

---

## Credentials reference

Keep this filled in. Store actual secret values in `.env`, not here.

| Variable | Where it comes from | Phase needed |
|---|---|---|
| `NOTION_TOKEN` | Notion My Integrations | Phase 0 |
| `NOTES_DB_ID` | Notion DB share URL | Phase 0 |
| `TASKS_DB_ID` | Notion DB share URL | Phase 0 |
| `CONTACTS_DB_ID` | Notion DB share URL | Week 2-3 |
| `PROJECTS_DB_ID` | Notion DB share URL | Week 2-3 |
| `OPPORTUNITIES_DB_ID` | Notion DB share URL | Week 9-12 |
| `DECISIONS_DB_ID` | Notion DB share URL | Week 9-12 |
| `COMPOSIO_API_KEY` | Composio Settings → API Keys | Week 2 |
| `OPENROUTER_API_KEY` | openrouter.ai → Keys | Week 2 |
| `NEWS_RSS_FEEDS` | Your choice (defaults in .env.example) | Phase 1 |
| `TIMEZONE` | Your local timezone string | Phase 1 |

Files that must **never** be committed to git (already in `.gitignore`):
- `.env`
- `credentials.json`
- `token.json`

If you ever accidentally commit any of these, **revoke the secret immediately** before anything else. GitHub scans for secrets and indexes them within minutes.

---

## Week 1 success criteria

- [ ] Daily Briefing appears in Notion Notes DB every morning at 05:00
- [ ] Briefing has three sections: News, Inbox, Schedule — all populated
- [ ] `launchctl list | grep virgil` shows the job as loaded
- [ ] iPhone alarm fires at 05:30 and sets a "Meeting Prep" alarm 45 min before first meeting
- [ ] You have not overslept a meeting since the shortcut was installed

When all five are checked, Week 1 is done. Start the Week 2 sprint.
