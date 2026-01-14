"""OAuth2 authentication handling for Google APIs with multi-account support."""

import json
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes for Gmail, Calendar, and Sheets access
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Config directory (can be overridden with ASSISTANT_CONFIG_DIR env var)
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "assistant"


def get_config_dir() -> Path:
    """Get the configuration directory, creating it if needed."""
    config_dir = Path(os.environ.get("ASSISTANT_CONFIG_DIR", DEFAULT_CONFIG_DIR))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_credentials_path() -> Path:
    """Get the path to the credentials.json file."""
    return get_config_dir() / "credentials.json"


def get_tokens_dir() -> Path:
    """Get the path to the tokens directory."""
    tokens_dir = get_config_dir() / "tokens"
    tokens_dir.mkdir(exist_ok=True)
    return tokens_dir


def get_config_path() -> Path:
    """Get the path to the config.json file."""
    return get_config_dir() / "config.json"


def get_token_path_for_account(email: str) -> Path:
    """Get the token file path for a specific account."""
    # Sanitize email for filename
    safe_email = email.replace("@", "_at_").replace(".", "_")
    return get_tokens_dir() / f"token_{safe_email}.json"


def _get_email_from_token(token_path: Path) -> Optional[str]:
    """Extract email from token by querying Gmail API."""
    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        from googleapiclient.discovery import build
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress")
    except Exception:
        return None


def load_config() -> dict:
    """Load the config file."""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    """Save the config file."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def get_active_account() -> Optional[str]:
    """Get the currently active account email."""
    config = load_config()
    active = config.get("active_account")

    # Verify the active account still has a valid token
    if active:
        token_path = get_token_path_for_account(active)
        if token_path.exists():
            return active

    # If no active account or token missing, try to find one
    accounts = list_accounts()
    if accounts:
        # Set the first available account as active
        set_active_account(accounts[0])
        return accounts[0]

    return None


def set_active_account(email: str) -> bool:
    """Set the active account."""
    token_path = get_token_path_for_account(email)
    if not token_path.exists():
        return False

    config = load_config()
    config["active_account"] = email
    save_config(config)
    return True


def list_accounts() -> list[str]:
    """List all authenticated accounts."""
    tokens_dir = get_tokens_dir()
    accounts = []

    for token_file in tokens_dir.glob("token_*.json"):
        email = _get_email_from_token(token_file)
        if email:
            accounts.append(email)

    return sorted(accounts)


def get_credentials(account: Optional[str] = None) -> Optional[Credentials]:
    """
    Get valid user credentials for the specified or active account.

    Args:
        account: Email of account to use, or None for active account.

    Returns:
        Credentials object if authenticated, None if credentials.json is missing.
    """
    # Determine which account to use
    if account is None:
        account = get_active_account()

    if account is None:
        # No accounts available, need to login
        return None

    token_path = get_token_path_for_account(account)
    credentials_path = get_credentials_path()
    creds = None

    # Load existing token if available
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token
            with open(token_path, "w") as token:
                token.write(creds.to_json())
        else:
            return None

    return creds


def login(set_as_active: bool = True, headless: bool = False) -> Optional[str]:
    """
    Initiate the OAuth login flow for a new or existing account.

    Args:
        set_as_active: Whether to set this account as the active account.
        headless: Use manual code entry flow for servers without a browser.

    Returns:
        Email of the logged-in account, or None if login failed.
    """
    credentials_path = get_credentials_path()

    if not credentials_path.exists():
        return None

    # Run OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        str(credentials_path), SCOPES
    )

    if headless:
        # Manual flow for headless servers
        flow.redirect_uri = "http://localhost:1"
        auth_url, _ = flow.authorization_url(prompt="consent")

        print(f"\nOpen this URL in your browser:\n\n{auth_url}\n")
        print("After authorizing, you'll be redirected to a URL that fails to load.")
        print("Copy the FULL URL from your browser's address bar and paste it here.\n")

        redirect_response = input("Paste the redirect URL: ").strip()

        # Extract the authorization code from the redirect URL
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(redirect_response)
        query_params = parse_qs(parsed.query)

        if "code" not in query_params:
            print("Error: Could not find authorization code in URL.")
            return None

        code = query_params["code"][0]
        flow.fetch_token(code=code)
        creds = flow.credentials
    else:
        creds = flow.run_local_server(port=0)

    # Get the email for this account
    from googleapiclient.discovery import build
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    email = profile.get("emailAddress")

    if not email:
        return None

    # Save the credentials
    token_path = get_token_path_for_account(email)
    with open(token_path, "w") as token:
        token.write(creds.to_json())

    # Set as active account if requested
    if set_as_active:
        set_active_account(email)

    return email


def logout(account: Optional[str] = None) -> bool:
    """
    Remove stored credentials for an account.

    Args:
        account: Email of account to logout, or None for active account.

    Returns:
        True if logout was successful, False if no credentials were stored.
    """
    if account is None:
        account = get_active_account()

    if account is None:
        return False

    token_path = get_token_path_for_account(account)

    if token_path.exists():
        os.remove(token_path)

        # If this was the active account, switch to another
        config = load_config()
        if config.get("active_account") == account:
            remaining = list_accounts()
            if remaining:
                set_active_account(remaining[0])
            else:
                config["active_account"] = None
                save_config(config)

        return True
    return False


def logout_all() -> int:
    """
    Remove all stored credentials.

    Returns:
        Number of accounts logged out.
    """
    accounts = list_accounts()
    count = 0
    for account in accounts:
        if logout(account):
            count += 1

    # Clear config
    config = load_config()
    config["active_account"] = None
    save_config(config)

    return count


def is_authenticated(account: Optional[str] = None) -> bool:
    """
    Check if user is currently authenticated.

    Args:
        account: Email of account to check, or None for active account.

    Returns:
        True if valid credentials exist, False otherwise.
    """
    if account is None:
        account = get_active_account()

    if account is None:
        return False

    token_path = get_token_path_for_account(account)

    if not token_path.exists():
        return False

    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds.valid:
            return True
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token
            with open(token_path, "w") as token:
                token.write(creds.to_json())
            return True
    except Exception:
        return False

    return False


def get_user_email(account: Optional[str] = None) -> Optional[str]:
    """
    Get the email address of the authenticated user.

    Args:
        account: Email of account to check, or None for active account.

    Returns:
        Email address string if available, None otherwise.
    """
    if account is None:
        account = get_active_account()

    if account is None:
        return None

    token_path = get_token_path_for_account(account)

    if not token_path.exists():
        return None

    return _get_email_from_token(token_path)


def require_auth(func):
    """Decorator to require authentication before running a function."""
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            from .utils import display_error
            display_error(
                "Not authenticated. Run 'assistant auth login' first."
            )
            raise SystemExit(1)
        return func(*args, **kwargs)

    return wrapper
