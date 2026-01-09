"""Calendar CLI commands."""

from datetime import datetime
from typing import Optional

import typer

from ..auth import is_authenticated
from ..utils.display import (
    console,
    display_error,
    display_success,
    format_calendar_events,
    format_calendars,
    format_event_detail,
    confirm,
)
from .client import CalendarClient

app = typer.Typer(help="Google Calendar commands")


def require_auth():
    """Check authentication and exit if not authenticated."""
    if not is_authenticated():
        display_error("Not authenticated. Run 'assistant auth login' first.")
        raise typer.Exit(1)


@app.command("list")
def list_events(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to show"),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum events to show"),
    calendar: Optional[str] = typer.Option(None, "--calendar", "-c", help="Calendar ID"),
):
    """List upcoming events."""
    require_auth()

    client = CalendarClient()
    try:
        calendar_id = calendar or "primary"
        events = client.get_upcoming_events(days=days, max_results=limit, calendar_id=calendar_id)

        if not events:
            console.print(f"No events in the next {days} days.")
            return

        table = format_calendar_events(events)
        console.print(table)
        console.print(f"\n[dim]{len(events)} events in the next {days} days[/dim]")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("today")
def today_events():
    """Show today's events."""
    require_auth()

    client = CalendarClient()
    try:
        events = client.get_today_events()

        if not events:
            console.print("No events today.")
            return

        table = format_calendar_events(events)
        console.print("[bold]Today's Events[/bold]")
        console.print(table)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("week")
def week_events():
    """Show this week's events."""
    require_auth()

    client = CalendarClient()
    try:
        events = client.get_week_events()

        if not events:
            console.print("No events this week.")
            return

        table = format_calendar_events(events)
        console.print("[bold]This Week's Events[/bold]")
        console.print(table)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("show")
def show_event(
    event_id: str = typer.Argument(..., help="Event ID to show"),
    calendar: Optional[str] = typer.Option(None, "--calendar", "-c", help="Calendar ID"),
):
    """Show details of a specific event."""
    require_auth()

    client = CalendarClient()
    try:
        if calendar:
            event = client.get_event(event_id, calendar_id=calendar)
        else:
            # Try to find across all calendars
            event = client.find_event_by_id(event_id)

        if not event:
            display_error(f"Event not found: {event_id}")
            raise typer.Exit(1)

        panel = format_event_detail(event)
        console.print(panel)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("calendars")
def list_calendars():
    """List all available calendars."""
    require_auth()

    client = CalendarClient()
    try:
        calendars = client.list_calendars()
        table = format_calendars(calendars)
        console.print(table)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("create")
def create_event(
    title: str = typer.Option(..., "--title", "-t", help="Event title"),
    start: str = typer.Option(..., "--start", "-s", help="Start time (e.g., '2024-01-15 14:00' or 'tomorrow 3pm')"),
    end: Optional[str] = typer.Option(None, "--end", "-e", help="End time (default: 1 hour after start)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Event description"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Event location"),
    attendees: Optional[list[str]] = typer.Option(None, "--attendee", "-a", help="Attendee emails"),
    calendar: Optional[str] = typer.Option(None, "--calendar", "-c", help="Calendar ID"),
    all_day: bool = typer.Option(False, "--all-day", help="Create an all-day event"),
    recurrence: Optional[str] = typer.Option(None, "--recurrence", "-r", help="Recurrence rule (e.g., 'FREQ=WEEKLY;BYDAY=TU,TH')"),
):
    """Create a new calendar event."""
    require_auth()

    client = CalendarClient()
    try:
        # Build recurrence list if provided
        recurrence_list = None
        if recurrence:
            # Ensure RRULE: prefix
            if not recurrence.startswith("RRULE:"):
                recurrence = f"RRULE:{recurrence}"
            recurrence_list = [recurrence]

        result = client.create_event(
            summary=title,
            start=start,
            end=end,
            description=description or "",
            location=location or "",
            attendees=attendees,
            calendar_id=calendar or "primary",
            all_day=all_day,
            recurrence=recurrence_list,
        )
        display_success(f"Event created: {result['summary']}")
        if result.get("htmlLink"):
            console.print(f"[dim]Link: {result['htmlLink']}[/dim]")
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("quick")
def quick_add(
    text: str = typer.Argument(..., help="Natural language event description"),
    calendar: Optional[str] = typer.Option(None, "--calendar", "-c", help="Calendar ID"),
):
    """Create an event using natural language.

    Examples:
        assistant calendar quick "Meeting with John tomorrow at 3pm"
        assistant calendar quick "Lunch on Friday at noon for 2 hours"
    """
    require_auth()

    client = CalendarClient()
    try:
        result = client.quick_add(text=text, calendar_id=calendar or "primary")
        display_success(f"Event created: {result['summary']}")

        # Show parsed time
        start = result.get("start", {})
        if "dateTime" in start:
            console.print(f"[dim]Scheduled for: {start['dateTime']}[/dim]")
        elif "date" in start:
            console.print(f"[dim]Scheduled for: {start['date']} (all day)[/dim]")

        if result.get("htmlLink"):
            console.print(f"[dim]Link: {result['htmlLink']}[/dim]")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("edit")
def edit_event(
    event_id: str = typer.Argument(..., help="Event ID to edit"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="New title"),
    start: Optional[str] = typer.Option(None, "--start", "-s", help="New start time"),
    end: Optional[str] = typer.Option(None, "--end", "-e", help="New end time"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="New location"),
    calendar: Optional[str] = typer.Option(None, "--calendar", "-c", help="Calendar ID"),
):
    """Edit an existing calendar event."""
    require_auth()

    if not any([title, start, end, description, location]):
        display_error("Specify at least one field to update (--title, --start, --end, --description, --location).")
        raise typer.Exit(1)

    client = CalendarClient()
    try:
        result = client.update_event(
            event_id=event_id,
            calendar_id=calendar or "primary",
            summary=title,
            start=start,
            end=end,
            description=description,
            location=location,
        )
        display_success(f"Event updated: {result['summary']}")
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("delete")
def delete_event(
    event_id: str = typer.Argument(..., help="Event ID to delete"),
    calendar: Optional[str] = typer.Option(None, "--calendar", "-c", help="Calendar ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a calendar event."""
    require_auth()

    if not yes and not confirm(f"Delete event {event_id}?"):
        console.print("Cancelled.")
        return

    client = CalendarClient()
    try:
        client.delete_event(event_id=event_id, calendar_id=calendar or "primary")
        display_success("Event deleted.")
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("respond")
def respond_to_event(
    event_id: str = typer.Argument(..., help="Event ID to respond to"),
    accept: bool = typer.Option(False, "--accept", "-y", help="Accept the invitation"),
    decline: bool = typer.Option(False, "--decline", "-n", help="Decline the invitation"),
    tentative: bool = typer.Option(False, "--tentative", "-m", help="Mark as tentative/maybe"),
    calendar: Optional[str] = typer.Option(None, "--calendar", "-c", help="Calendar ID"),
):
    """Respond to an event invitation."""
    require_auth()

    # Determine response
    responses = [("accepted", accept), ("declined", decline), ("tentative", tentative)]
    selected = [r for r, flag in responses if flag]

    if len(selected) != 1:
        display_error("Specify exactly one of: --accept, --decline, or --tentative")
        raise typer.Exit(1)

    response = selected[0]

    client = CalendarClient()
    try:
        client.respond_to_event(
            event_id=event_id,
            response=response,
            calendar_id=calendar or "primary",
        )
        display_success(f"Response updated: {response}")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)
