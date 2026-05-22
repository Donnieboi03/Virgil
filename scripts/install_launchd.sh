#!/usr/bin/env bash
# install_launchd.sh — install the Virgil ingestion job on macOS
#
# Runs src/ingestion.py once a day via launchd. The time of day is read from
# INGESTION_HOUR and INGESTION_MINUTE in .env (defaults: 05:00).
#
# Usage:
#   chmod +x scripts/install_launchd.sh
#   ./scripts/install_launchd.sh
#
# To change the schedule later: edit INGESTION_HOUR / INGESTION_MINUTE in .env
# and rerun this script.
#
# To uninstall:
#   launchctl unload ~/Library/LaunchAgents/com.virgil.ingestion.plist
#   rm ~/Library/LaunchAgents/com.virgil.ingestion.plist
#
# ── Linux fallback (crontab) ────────────────────────────────────────────────
# If you're on Linux or a VPS, use crontab instead:
#
#   crontab -e
#
# Add this line (replace the path placeholders and the time):
#
#   0 5 * * * cd /path/to/virgil && /path/to/virgil/.venv/bin/python -m src.ingestion >> /path/to/virgil/logs/ingestion.log 2>&1
#
# ── macOS Full Disk Access note ─────────────────────────────────────────────
# On macOS 13+, launchd jobs run by your user agent have full access by default.
# If the job fails silently (runs but can't read credentials.json), grant FDA:
#   System Settings → Privacy & Security → Full Disk Access → + → /usr/libexec/launchd
# ────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"
PLIST_TEMPLATE="${REPO_ROOT}/scripts/com.virgil.ingestion.plist"
PLIST_DEST="${HOME}/Library/LaunchAgents/com.virgil.ingestion.plist"

# Verify the virtualenv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Virtual environment not found at ${VENV_PYTHON}"
    echo "       Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Verify .env exists
if [ ! -f "${REPO_ROOT}/.env" ]; then
    echo "ERROR: .env not found. Copy .env.example to .env and fill in values first."
    exit 1
fi

# Load INGESTION_HOUR / INGESTION_MINUTE from .env (allowing them to be unset).
# Use a subshell + set -a so we don't pollute the parent shell with the rest of
# .env's contents (e.g. NOTION_TOKEN). Only the two values we care about leak out.
ENV_HOUR=$(set -a; . "${REPO_ROOT}/.env"; set +a; printf '%s' "${INGESTION_HOUR:-}")
ENV_MINUTE=$(set -a; . "${REPO_ROOT}/.env"; set +a; printf '%s' "${INGESTION_MINUTE:-}")

INGESTION_HOUR="${ENV_HOUR:-5}"
INGESTION_MINUTE="${ENV_MINUTE:-0}"

# Validate that they are integers in the allowed ranges.
if ! [[ "$INGESTION_HOUR" =~ ^[0-9]+$ ]] || [ "$INGESTION_HOUR" -lt 0 ] || [ "$INGESTION_HOUR" -gt 23 ]; then
    echo "ERROR: INGESTION_HOUR must be an integer 0-23 (got: '${INGESTION_HOUR}')."
    echo "       Fix it in ${REPO_ROOT}/.env and rerun."
    exit 1
fi

if ! [[ "$INGESTION_MINUTE" =~ ^[0-9]+$ ]] || [ "$INGESTION_MINUTE" -lt 0 ] || [ "$INGESTION_MINUTE" -gt 59 ]; then
    echo "ERROR: INGESTION_MINUTE must be an integer 0-59 (got: '${INGESTION_MINUTE}')."
    echo "       Fix it in ${REPO_ROOT}/.env and rerun."
    exit 1
fi

# Pretty-print the schedule for the final summary (HH:MM in 24h).
SCHEDULE_PRETTY="$(printf '%02d:%02d' "$INGESTION_HOUR" "$INGESTION_MINUTE")"

# Create LaunchAgents dir if needed
mkdir -p "${HOME}/Library/LaunchAgents"

# Substitute placeholders in the plist template
sed \
    -e "s|VENV_PYTHON_PLACEHOLDER|${VENV_PYTHON}|g" \
    -e "s|REPO_ROOT_PLACEHOLDER|${REPO_ROOT}|g" \
    -e "s|HOUR_PLACEHOLDER|${INGESTION_HOUR}|g" \
    -e "s|MINUTE_PLACEHOLDER|${INGESTION_MINUTE}|g" \
    "$PLIST_TEMPLATE" > "$PLIST_DEST"

echo "Wrote plist to: ${PLIST_DEST}"

# Unload existing job if present (ignore error if not loaded)
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load the new job
launchctl load "$PLIST_DEST"

echo ""
echo "Virgil ingestion job installed and loaded."
echo "It will run automatically at ${SCHEDULE_PRETTY} every day (Mac local time)."
echo ""
echo "Verify with:   launchctl list | grep virgil"
echo "Run manually:  launchctl start com.virgil.ingestion"
echo "View logs:     tail -f ${REPO_ROOT}/logs/ingestion.log"
echo ""
echo "To change the time later: edit INGESTION_HOUR / INGESTION_MINUTE in .env"
echo "and rerun this script."
echo ""
echo "REMINDER: Make sure macOS Full Disk Access is granted if the job"
echo "fails silently. See script comments for instructions."
