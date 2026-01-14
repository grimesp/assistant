"""Main CLI entry point for Assistant."""

from typing import Optional

import typer

from . import __version__
from .auth import (
    get_active_account,
    get_credentials_path,
    get_tokens_dir,
    get_user_email,
    is_authenticated,
    list_accounts,
    login,
    logout,
    logout_all,
    set_active_account,
)
from .gmail.commands import app as gmail_app
from .calendar.commands import app as calendar_app
from .sheets.commands import app as sheets_app
from .drive.commands import app as drive_app
from .utils.display import console, display_error, display_success, display_warning

app = typer.Typer(
    name="assistant",
    help="CLI tool for Gmail, Google Calendar, Google Sheets, and Google Drive",
    no_args_is_help=True,
)

# Add subcommands
app.add_typer(gmail_app, name="gmail")
app.add_typer(calendar_app, name="calendar")
app.add_typer(sheets_app, name="sheets")
app.add_typer(drive_app, name="drive")

# Auth subcommand group
auth_app = typer.Typer(help="Authentication commands")
app.add_typer(auth_app, name="auth")


@auth_app.command("login")
def auth_login(
    headless: bool = typer.Option(
        False, "--headless", help="Use console-based auth flow for headless servers"
    ),
):
    """Authenticate with Google (Gmail and Calendar).

    You can login to multiple accounts. Each new login adds an account.
    The newly logged-in account becomes the active account.

    Use --headless on servers without a browser.
    """
    credentials_path = get_credentials_path()

    if not credentials_path.exists():
        display_error(
            f"credentials.json not found at {credentials_path}\n\n"
            "To set up Google Cloud credentials:\n"
            "1. Go to https://console.cloud.google.com/\n"
            "2. Create a new project or select an existing one\n"
            "3. Enable the Gmail API and Google Calendar API\n"
            "4. Go to Credentials > Create Credentials > OAuth client ID\n"
            "5. Choose 'Desktop app' as the application type\n"
            "6. Download the credentials and save as 'credentials.json' in the project directory\n"
            "\nSee README.md for detailed instructions."
        )
        raise typer.Exit(1)

    if headless:
        console.print("Starting console-based authentication...")
        console.print("[dim]You'll receive a URL to open in any browser.[/dim]")
    else:
        console.print("Opening browser for Google authentication...")
        console.print("[dim]You'll be asked to grant access to Gmail and Calendar.[/dim]")

    email = login(headless=headless)
    if email:
        display_success(f"Successfully authenticated as {email}!")

        # Show all accounts
        accounts = list_accounts()
        if len(accounts) > 1:
            console.print(f"\n[dim]You now have {len(accounts)} accounts. Use 'assistant auth list' to see all.[/dim]")
    else:
        display_error("Authentication failed.")
        raise typer.Exit(1)


@auth_app.command("logout")
def auth_logout(
    account: Optional[str] = typer.Argument(None, help="Email of account to logout (default: active account)"),
    all_accounts: bool = typer.Option(False, "--all", "-a", help="Logout all accounts"),
):
    """Sign out and remove stored credentials.

    With no arguments, logs out the active account.
    Use --all to logout all accounts.
    """
    if all_accounts:
        count = logout_all()
        if count > 0:
            display_success(f"Logged out {count} account(s).")
        else:
            display_warning("No accounts to log out.")
        return

    target = account or get_active_account()

    if target is None:
        display_warning("Not currently authenticated.")
        return

    if logout(target):
        display_success(f"Successfully logged out {target}.")

        # Show remaining accounts
        remaining = list_accounts()
        if remaining:
            active = get_active_account()
            console.print(f"[dim]Active account is now: {active}[/dim]")
    else:
        display_warning(f"No credentials found for {target}.")


@auth_app.command("status")
def auth_status():
    """Check authentication status."""
    accounts = list_accounts()

    if not accounts:
        console.print("[bold red]Not authenticated[/bold red]")
        console.print("Run 'assistant auth login' to authenticate.")
        return

    active = get_active_account()
    console.print(f"[bold green]Authenticated[/bold green] with {len(accounts)} account(s)\n")

    for acc in accounts:
        if acc == active:
            console.print(f"  [bold cyan]● {acc}[/bold cyan] [dim](active)[/dim]")
        else:
            console.print(f"  [dim]○ {acc}[/dim]")

    console.print(f"\n[dim]Tokens stored in: {get_tokens_dir()}[/dim]")


@auth_app.command("list")
def auth_list():
    """List all authenticated accounts."""
    accounts = list_accounts()

    if not accounts:
        console.print("No authenticated accounts.")
        console.print("[dim]Run 'assistant auth login' to add an account.[/dim]")
        return

    active = get_active_account()

    from rich.table import Table
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("", width=2)
    table.add_column("Account")
    table.add_column("Status", width=10)

    for acc in accounts:
        if acc == active:
            table.add_row("●", f"[bold]{acc}[/bold]", "[cyan]active[/cyan]")
        else:
            table.add_row("○", acc, "")

    console.print(table)
    console.print(f"\n[dim]{len(accounts)} account(s)[/dim]")


@auth_app.command("switch")
def auth_switch(
    account: str = typer.Argument(..., help="Email of account to switch to"),
):
    """Switch the active account."""
    accounts = list_accounts()

    if not accounts:
        display_error("No authenticated accounts. Run 'assistant auth login' first.")
        raise typer.Exit(1)

    # Allow partial match
    matches = [a for a in accounts if account.lower() in a.lower()]

    if len(matches) == 0:
        display_error(f"Account '{account}' not found.")
        console.print("\nAvailable accounts:")
        for acc in accounts:
            console.print(f"  - {acc}")
        raise typer.Exit(1)
    elif len(matches) > 1:
        display_error(f"'{account}' matches multiple accounts:")
        for acc in matches:
            console.print(f"  - {acc}")
        console.print("\nPlease be more specific.")
        raise typer.Exit(1)

    target = matches[0]

    if set_active_account(target):
        display_success(f"Switched to {target}")
    else:
        display_error(f"Failed to switch to {target}")
        raise typer.Exit(1)


@app.command("version")
def version():
    """Show version information."""
    console.print(f"Assistant CLI v{__version__}")


@app.callback()
def main():
    """
    Assistant - CLI tool for Gmail, Google Calendar, Google Sheets, and Google Drive.

    Use 'assistant auth login' to authenticate, then use the gmail, calendar,
    sheets, and drive subcommands to interact with your accounts.

    Supports multiple accounts - use 'assistant auth list' to see all accounts
    and 'assistant auth switch' to change the active account.
    """
    pass


if __name__ == "__main__":
    app()
