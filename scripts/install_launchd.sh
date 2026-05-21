#!/usr/bin/env bash
# install_launchd.sh — install the Virgil ingestion job on macOS
#
# Runs src/ingestion.py at 05:00 AM daily via launchd.
#
# Usage:
#   chmod +x scripts/install_launchd.sh
#   ./scripts/install_launchd.sh
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
# Add this line (replace the path placeholders):
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

# Create LaunchAgents dir if needed
mkdir -p "${HOME}/Library/LaunchAgents"

# Substitute placeholders in the plist template
sed \
    -e "s|VENV_PYTHON_PLACEHOLDER|${VENV_PYTHON}|g" \
    -e "s|REPO_ROOT_PLACEHOLDER|${REPO_ROOT}|g" \
    "$PLIST_TEMPLATE" > "$PLIST_DEST"

echo "Wrote plist to: ${PLIST_DEST}"

# Unload existing job if present (ignore error if not loaded)
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load the new job
launchctl load "$PLIST_DEST"

echo ""
echo "Virgil ingestion job installed and loaded."
echo "It will run automatically at 05:00 AM every day."
echo ""
echo "Verify with:   launchctl list | grep virgil"
echo "Run manually:  launchctl start com.virgil.ingestion"
echo "View logs:     tail -f ${REPO_ROOT}/logs/ingestion.log"
echo ""
echo "REMINDER: Make sure macOS Full Disk Access is granted if the job"
echo "fails silently. See script comments for instructions."
