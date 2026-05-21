from __future__ import annotations

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .config import get as get_config

# Read-only scopes. Virgil never writes to Gmail or Calendar directly —
# writes go through Composio (Week 2+) which holds its own OAuth tokens.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def _credentials() -> Credentials:
    cfg = get_config()
    creds: Credentials | None = None

    if cfg.token_path.exists():
        creds = Credentials.from_authorized_user_file(str(cfg.token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not cfg.credentials_path.exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {cfg.credentials_path}. "
                    "Complete NEXTSTEPS.md Phase 1 Step 2 first."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(cfg.credentials_path), SCOPES
            )
            # run_local_server opens a browser for the first-time auth flow.
            # On a headless server, swap this for flow.run_console() which
            # prints a URL and reads the code from stdin instead.
            creds = flow.run_local_server(port=0)

        cfg.token_path.write_text(creds.to_json())

    return creds


def gmail():
    """Return an authenticated Gmail API service (read-only)."""
    return build("gmail", "v1", credentials=_credentials(), cache_discovery=False)


def calendar():
    """Return an authenticated Google Calendar API service (read-only)."""
    return build("calendar", "v3", credentials=_credentials(), cache_discovery=False)
