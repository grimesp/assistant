"""Rich display utilities for the Assistant CLI."""

import os
import subprocess
import tempfile
from datetime import datetime
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown

console = Console()


def display_error(message: str) -> None:
    """Display an error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def display_success(message: str) -> None:
    """Display a success message."""
    console.print(f"[bold green]Success:[/bold green] {message}")


def display_warning(message: str) -> None:
    """Display a warning message."""
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")


def display_info(message: str) -> None:
    """Display an info message."""
    console.print(f"[bold blue]Info:[/bold blue] {message}")


def format_email_list(emails: list[dict]) -> Table:
    """
    Format a list of emails as a Rich table.

    Args:
        emails: List of email dictionaries with id, from, subject, date, snippet, unread

    Returns:
        Rich Table object
    """
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("ID", style="dim", width=12)
    table.add_column("From", width=25, overflow="ellipsis")
    table.add_column("Subject", width=40, overflow="ellipsis")
    table.add_column("Date", width=12)
    table.add_column("", width=3)  # Unread indicator

    for email in emails:
        unread = "[bold]*[/bold]" if email.get("unread", False) else ""
        from_addr = email.get("from", "Unknown")
        # Extract just the name or email, not the full header
        if "<" in from_addr:
            from_addr = from_addr.split("<")[0].strip().strip('"')

        subject = email.get("subject", "(No Subject)")
        if email.get("unread", False):
            subject = f"[bold]{subject}[/bold]"

        date_str = email.get("date", "")
        if date_str:
            try:
                # Try to parse and format the date
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                date_str = dt.strftime("%b %d")
            except (ValueError, AttributeError):
                pass

        table.add_row(
            email.get("id", "")[:12],
            from_addr[:25],
            subject[:40],
            date_str,
            unread,
        )

    return table


def format_email_detail(email: dict) -> Panel:
    """
    Format a single email for detailed display.

    Args:
        email: Email dictionary with full details

    Returns:
        Rich Panel object
    """
    # Build header section
    header_lines = [
        f"[bold cyan]From:[/bold cyan] {email.get('from', 'Unknown')}",
        f"[bold cyan]To:[/bold cyan] {email.get('to', 'Unknown')}",
    ]

    if email.get("cc"):
        header_lines.append(f"[bold cyan]Cc:[/bold cyan] {email['cc']}")

    header_lines.extend([
        f"[bold cyan]Date:[/bold cyan] {email.get('date', 'Unknown')}",
        f"[bold cyan]Subject:[/bold cyan] {email.get('subject', '(No Subject)')}",
    ])

    if email.get("attachments"):
        att_list = ", ".join(email["attachments"])
        header_lines.append(f"[bold cyan]Attachments:[/bold cyan] {att_list}")

    header = "\n".join(header_lines)

    # Build body section
    body = email.get("body", "")

    # Combine into panel
    content = f"{header}\n\n{'─' * 60}\n\n{body}"

    return Panel(
        content,
        title=f"[bold]Message: {email.get('id', '')[:12]}[/bold]",
        border_style="cyan",
    )


def format_calendar_events(events: list[dict]) -> Table:
    """
    Format a list of calendar events as a Rich table.

    Args:
        events: List of event dictionaries

    Returns:
        Rich Table object
    """
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("ID", style="dim", width=12)
    table.add_column("Title", width=35, overflow="ellipsis")
    table.add_column("Start", width=18)
    table.add_column("End", width=18)
    table.add_column("Calendar", width=15, overflow="ellipsis")

    for event in events:
        start = event.get("start", {})
        end = event.get("end", {})

        # Handle all-day vs timed events
        if "date" in start:
            start_str = start["date"]
            end_str = end.get("date", "")
        else:
            start_dt = start.get("dateTime", "")
            end_dt = end.get("dateTime", "")
            try:
                if start_dt:
                    dt = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
                    start_str = dt.strftime("%b %d %I:%M %p")
                else:
                    start_str = ""
                if end_dt:
                    dt = datetime.fromisoformat(end_dt.replace("Z", "+00:00"))
                    end_str = dt.strftime("%b %d %I:%M %p")
                else:
                    end_str = ""
            except (ValueError, AttributeError):
                start_str = start_dt[:16] if start_dt else ""
                end_str = end_dt[:16] if end_dt else ""

        table.add_row(
            event.get("id", "")[:12],
            event.get("summary", "(No Title)")[:35],
            start_str,
            end_str,
            event.get("calendar_name", "")[:15],
        )

    return table


def format_event_detail(event: dict) -> Panel:
    """
    Format a single calendar event for detailed display.

    Args:
        event: Event dictionary with full details

    Returns:
        Rich Panel object
    """
    lines = [
        f"[bold magenta]Title:[/bold magenta] {event.get('summary', '(No Title)')}",
    ]

    start = event.get("start", {})
    end = event.get("end", {})

    if "date" in start:
        lines.append(f"[bold magenta]Date:[/bold magenta] {start['date']} (All day)")
    else:
        start_dt = start.get("dateTime", "")
        end_dt = end.get("dateTime", "")
        if start_dt:
            try:
                dt = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
                lines.append(f"[bold magenta]Start:[/bold magenta] {dt.strftime('%B %d, %Y at %I:%M %p')}")
            except ValueError:
                lines.append(f"[bold magenta]Start:[/bold magenta] {start_dt}")
        if end_dt:
            try:
                dt = datetime.fromisoformat(end_dt.replace("Z", "+00:00"))
                lines.append(f"[bold magenta]End:[/bold magenta] {dt.strftime('%B %d, %Y at %I:%M %p')}")
            except ValueError:
                lines.append(f"[bold magenta]End:[/bold magenta] {end_dt}")

    if event.get("location"):
        lines.append(f"[bold magenta]Location:[/bold magenta] {event['location']}")

    if event.get("description"):
        lines.append(f"\n[bold magenta]Description:[/bold magenta]\n{event['description']}")

    if event.get("attendees"):
        attendee_list = []
        for att in event["attendees"]:
            email = att.get("email", "")
            status = att.get("responseStatus", "")
            if status == "accepted":
                status_icon = "[green]Y[/green]"
            elif status == "declined":
                status_icon = "[red]N[/red]"
            elif status == "tentative":
                status_icon = "[yellow]?[/yellow]"
            else:
                status_icon = "[dim]-[/dim]"
            attendee_list.append(f"  {status_icon} {email}")
        lines.append(f"\n[bold magenta]Attendees:[/bold magenta]\n" + "\n".join(attendee_list))

    if event.get("htmlLink"):
        lines.append(f"\n[dim]Link: {event['htmlLink']}[/dim]")

    content = "\n".join(lines)

    return Panel(
        content,
        title=f"[bold]Event: {event.get('id', '')[:12]}[/bold]",
        border_style="magenta",
    )


def format_labels(labels: list[dict]) -> Table:
    """
    Format Gmail labels as a Rich table.

    Args:
        labels: List of label dictionaries

    Returns:
        Rich Table object
    """
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Name", width=30)
    table.add_column("Type", width=15)
    table.add_column("Messages", width=10, justify="right")
    table.add_column("Unread", width=10, justify="right")

    for label in labels:
        table.add_row(
            label.get("name", ""),
            label.get("type", ""),
            str(label.get("messagesTotal", "")),
            str(label.get("messagesUnread", "")),
        )

    return table


def format_drafts(drafts: list[dict]) -> Table:
    """
    Format a list of drafts as a Rich table.

    Args:
        drafts: List of draft dictionaries

    Returns:
        Rich Table object
    """
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("ID", style="dim", width=12)
    table.add_column("To", width=25, overflow="ellipsis")
    table.add_column("Subject", width=40, overflow="ellipsis")

    for draft in drafts:
        table.add_row(
            draft.get("id", "")[:12],
            draft.get("to", "")[:25],
            draft.get("subject", "(No Subject)")[:40],
        )

    return table


def format_calendars(calendars: list[dict]) -> Table:
    """
    Format a list of calendars as a Rich table.

    Args:
        calendars: List of calendar dictionaries

    Returns:
        Rich Table object
    """
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("ID", style="dim", width=40)
    table.add_column("Name", width=30)
    table.add_column("Access", width=15)

    for cal in calendars:
        access = cal.get("accessRole", "")
        if access == "owner":
            access = "[green]owner[/green]"
        elif access == "writer":
            access = "[yellow]writer[/yellow]"
        else:
            access = f"[dim]{access}[/dim]"

        table.add_row(
            cal.get("id", "")[:40],
            cal.get("summary", "")[:30],
            access,
        )

    return table


def format_attachments(attachments: list[dict]) -> Table:
    """
    Format a list of attachments as a Rich table.

    Args:
        attachments: List of attachment dictionaries

    Returns:
        Rich Table object
    """
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("#", width=3, justify="right")
    table.add_column("Filename", width=40, overflow="ellipsis")
    table.add_column("Size", width=12, justify="right")
    table.add_column("Type", width=25, overflow="ellipsis")

    for idx, att in enumerate(attachments, 1):
        size = att.get("size", 0)
        if size > 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        elif size > 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} B"

        table.add_row(
            str(idx),
            att.get("filename", "Unknown"),
            size_str,
            att.get("mimeType", ""),
        )

    return table


def open_editor(initial_content: str = "") -> Optional[str]:
    """
    Open the user's preferred editor to compose text.

    Args:
        initial_content: Optional initial content to populate the editor with

    Returns:
        The edited content, or None if the editor was closed without saving
    """
    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "vim"))

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(initial_content)
        temp_path = f.name

    try:
        result = subprocess.run([editor, temp_path])
        if result.returncode != 0:
            return None

        with open(temp_path, "r") as f:
            content = f.read()

        # Return None if content is unchanged or empty
        if content.strip() == initial_content.strip():
            return None

        return content.strip()
    finally:
        os.unlink(temp_path)


def confirm(message: str, default: bool = False) -> bool:
    """
    Ask for confirmation from the user.

    Args:
        message: The confirmation message
        default: Default value if user just presses enter

    Returns:
        True if confirmed, False otherwise
    """
    suffix = "[Y/n]" if default else "[y/N]"
    response = console.input(f"{message} {suffix} ")

    if not response:
        return default

    return response.lower() in ("y", "yes")
