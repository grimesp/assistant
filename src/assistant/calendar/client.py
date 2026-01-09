"""Google Calendar API client wrapper."""

from datetime import datetime, timedelta
from typing import Any, Optional

from dateutil import parser as dateparser
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..auth import get_credentials


class CalendarClient:
    """Wrapper class for Google Calendar API operations."""

    def __init__(self):
        """Initialize the Calendar client."""
        self._service = None

    @property
    def service(self):
        """Get or create the Calendar API service."""
        if self._service is None:
            creds = get_credentials()
            if creds is None:
                raise RuntimeError("Not authenticated. Run 'assistant auth login' first.")
            self._service = build("calendar", "v3", credentials=creds)
        return self._service

    def list_calendars(self) -> list[dict]:
        """
        List all calendars the user has access to.

        Returns:
            List of calendar dictionaries
        """
        try:
            calendar_list = self.service.calendarList().list().execute()
            calendars = calendar_list.get("items", [])

            result = []
            for cal in calendars:
                result.append({
                    "id": cal["id"],
                    "summary": cal.get("summary", ""),
                    "description": cal.get("description", ""),
                    "primary": cal.get("primary", False),
                    "accessRole": cal.get("accessRole", ""),
                    "backgroundColor": cal.get("backgroundColor", ""),
                    "foregroundColor": cal.get("foregroundColor", ""),
                    "timeZone": cal.get("timeZone", ""),
                })

            return result
        except HttpError as e:
            raise RuntimeError(f"Calendar API error: {e}")

    def get_primary_calendar_id(self) -> str:
        """Get the primary calendar ID."""
        calendars = self.list_calendars()
        for cal in calendars:
            if cal.get("primary"):
                return cal["id"]
        return "primary"

    def get_calendar_timezone(self, calendar_id: str = "primary") -> Optional[str]:
        """
        Get the timezone for a specific calendar.

        Args:
            calendar_id: The calendar ID

        Returns:
            Timezone string (e.g., 'America/Denver') or None
        """
        try:
            cal = self.service.calendars().get(calendarId=calendar_id).execute()
            return cal.get("timeZone")
        except HttpError:
            return None

    def list_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 50,
        single_events: bool = True,
    ) -> list[dict]:
        """
        List events from a calendar.

        Args:
            calendar_id: The calendar ID (default: primary)
            time_min: Start time filter
            time_max: End time filter
            max_results: Maximum number of events to return
            single_events: If True, expand recurring events

        Returns:
            List of event dictionaries
        """
        try:
            params = {
                "calendarId": calendar_id,
                "maxResults": max_results,
                "singleEvents": single_events,
                "orderBy": "startTime",
            }

            if time_min:
                # Use isoformat with timezone info, or assume local time
                if time_min.tzinfo is None:
                    params["timeMin"] = time_min.astimezone().isoformat()
                else:
                    params["timeMin"] = time_min.isoformat()
            if time_max:
                if time_max.tzinfo is None:
                    params["timeMax"] = time_max.astimezone().isoformat()
                else:
                    params["timeMax"] = time_max.isoformat()

            events_result = self.service.events().list(**params).execute()
            events = events_result.get("items", [])

            # Get calendar name for display
            try:
                cal = self.service.calendars().get(calendarId=calendar_id).execute()
                calendar_name = cal.get("summary", calendar_id)
            except HttpError:
                calendar_name = calendar_id

            result = []
            for event in events:
                result.append({
                    "id": event["id"],
                    "summary": event.get("summary", "(No Title)"),
                    "description": event.get("description", ""),
                    "location": event.get("location", ""),
                    "start": event.get("start", {}),
                    "end": event.get("end", {}),
                    "status": event.get("status", ""),
                    "htmlLink": event.get("htmlLink", ""),
                    "attendees": event.get("attendees", []),
                    "organizer": event.get("organizer", {}),
                    "creator": event.get("creator", {}),
                    "calendar_id": calendar_id,
                    "calendar_name": calendar_name,
                    "recurrence": event.get("recurrence", []),
                    "recurringEventId": event.get("recurringEventId"),
                })

            return result
        except HttpError as e:
            raise RuntimeError(f"Calendar API error: {e}")

    def get_event(self, event_id: str, calendar_id: str = "primary") -> Optional[dict]:
        """
        Get a single event by ID.

        Args:
            event_id: The event ID
            calendar_id: The calendar ID

        Returns:
            Event dictionary or None if not found
        """
        try:
            event = (
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )

            return {
                "id": event["id"],
                "summary": event.get("summary", "(No Title)"),
                "description": event.get("description", ""),
                "location": event.get("location", ""),
                "start": event.get("start", {}),
                "end": event.get("end", {}),
                "status": event.get("status", ""),
                "htmlLink": event.get("htmlLink", ""),
                "attendees": event.get("attendees", []),
                "organizer": event.get("organizer", {}),
                "creator": event.get("creator", {}),
                "calendar_id": calendar_id,
                "recurrence": event.get("recurrence", []),
            }
        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise RuntimeError(f"Calendar API error: {e}")

    def create_event(
        self,
        summary: str,
        start: datetime | str,
        end: Optional[datetime | str] = None,
        description: str = "",
        location: str = "",
        attendees: Optional[list[str]] = None,
        calendar_id: str = "primary",
        all_day: bool = False,
        timezone: Optional[str] = None,
        recurrence: Optional[list[str]] = None,
    ) -> dict:
        """
        Create a new calendar event.

        Args:
            summary: Event title
            start: Start time (datetime or string to parse)
            end: End time (datetime or string to parse, default: 1 hour after start)
            description: Event description
            location: Event location
            attendees: List of attendee email addresses
            calendar_id: The calendar ID
            all_day: If True, create an all-day event
            timezone: Timezone for the event
            recurrence: List of RRULE strings (e.g., ['RRULE:FREQ=WEEKLY;BYDAY=TU,TH'])

        Returns:
            Created event info
        """
        try:
            # Parse start time if string
            if isinstance(start, str):
                start = dateparser.parse(start)
                if start is None:
                    raise ValueError(f"Could not parse start time")

            # Parse or default end time
            if end is None:
                if all_day:
                    end = start + timedelta(days=1)
                else:
                    end = start + timedelta(hours=1)
            elif isinstance(end, str):
                end = dateparser.parse(end)
                if end is None:
                    raise ValueError(f"Could not parse end time")

            # Auto-fetch timezone from the target calendar if not provided
            if timezone is None and not all_day:
                timezone = self.get_calendar_timezone(calendar_id)

            event_body = {
                "summary": summary,
            }

            if description:
                event_body["description"] = description
            if location:
                event_body["location"] = location

            if all_day:
                event_body["start"] = {"date": start.strftime("%Y-%m-%d")}
                event_body["end"] = {"date": end.strftime("%Y-%m-%d")}
            else:
                start_dict = {"dateTime": start.isoformat()}
                end_dict = {"dateTime": end.isoformat()}
                if timezone:
                    start_dict["timeZone"] = timezone
                    end_dict["timeZone"] = timezone
                event_body["start"] = start_dict
                event_body["end"] = end_dict

            if attendees:
                event_body["attendees"] = [{"email": email} for email in attendees]

            if recurrence:
                event_body["recurrence"] = recurrence

            event = (
                self.service.events()
                .insert(calendarId=calendar_id, body=event_body)
                .execute()
            )

            return {
                "id": event["id"],
                "summary": event.get("summary"),
                "htmlLink": event.get("htmlLink", ""),
            }
        except HttpError as e:
            raise RuntimeError(f"Calendar API error: {e}")

    def quick_add(self, text: str, calendar_id: str = "primary") -> dict:
        """
        Create an event using natural language.

        Args:
            text: Natural language description (e.g., "Meeting with John tomorrow at 3pm")
            calendar_id: The calendar ID

        Returns:
            Created event info
        """
        try:
            event = (
                self.service.events()
                .quickAdd(calendarId=calendar_id, text=text)
                .execute()
            )

            return {
                "id": event["id"],
                "summary": event.get("summary", "(No Title)"),
                "start": event.get("start", {}),
                "end": event.get("end", {}),
                "htmlLink": event.get("htmlLink", ""),
            }
        except HttpError as e:
            raise RuntimeError(f"Calendar API error: {e}")

    def update_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        summary: Optional[str] = None,
        start: Optional[datetime | str] = None,
        end: Optional[datetime | str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> dict:
        """
        Update an existing event.

        Args:
            event_id: The event ID
            calendar_id: The calendar ID
            summary: New title (optional)
            start: New start time (optional)
            end: New end time (optional)
            description: New description (optional)
            location: New location (optional)

        Returns:
            Updated event info
        """
        try:
            # Get existing event
            event = (
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )

            # Update fields
            if summary is not None:
                event["summary"] = summary
            if description is not None:
                event["description"] = description
            if location is not None:
                event["location"] = location

            # Handle time updates
            # Get timezone for non-all-day events
            timezone = None
            if start is not None or end is not None:
                if "date" not in event.get("start", {}):
                    timezone = self.get_calendar_timezone(calendar_id)

            if start is not None:
                if isinstance(start, str):
                    start = dateparser.parse(start)
                    if start is None:
                        raise ValueError("Could not parse start time")

                # Check if this is an all-day event
                if "date" in event.get("start", {}):
                    event["start"] = {"date": start.strftime("%Y-%m-%d")}
                else:
                    start_dict = {"dateTime": start.isoformat()}
                    if timezone:
                        start_dict["timeZone"] = timezone
                    event["start"] = start_dict

            if end is not None:
                if isinstance(end, str):
                    end = dateparser.parse(end)
                    if end is None:
                        raise ValueError("Could not parse end time")

                if "date" in event.get("end", {}):
                    event["end"] = {"date": end.strftime("%Y-%m-%d")}
                else:
                    end_dict = {"dateTime": end.isoformat()}
                    if timezone:
                        end_dict["timeZone"] = timezone
                    event["end"] = end_dict

            updated = (
                self.service.events()
                .update(calendarId=calendar_id, eventId=event_id, body=event)
                .execute()
            )

            return {
                "id": updated["id"],
                "summary": updated.get("summary"),
                "htmlLink": updated.get("htmlLink", ""),
            }
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Event not found: {event_id}")
            raise RuntimeError(f"Calendar API error: {e}")

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> bool:
        """
        Delete an event.

        Args:
            event_id: The event ID
            calendar_id: The calendar ID

        Returns:
            True if successful
        """
        try:
            self.service.events().delete(
                calendarId=calendar_id, eventId=event_id
            ).execute()
            return True
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Event not found: {event_id}")
            raise RuntimeError(f"Calendar API error: {e}")

    def respond_to_event(
        self,
        event_id: str,
        response: str,
        calendar_id: str = "primary",
    ) -> bool:
        """
        Respond to an event invitation.

        Args:
            event_id: The event ID
            response: Response type (accepted, declined, tentative)
            calendar_id: The calendar ID

        Returns:
            True if successful
        """
        try:
            # Get current event
            event = (
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )

            # Get user's email to find them in attendees
            calendar_list = self.service.calendarList().list().execute()
            user_email = None
            for cal in calendar_list.get("items", []):
                if cal.get("primary"):
                    user_email = cal["id"]
                    break

            if not user_email:
                raise RuntimeError("Could not determine user email")

            # Update attendee response
            attendees = event.get("attendees", [])
            for attendee in attendees:
                if attendee.get("email", "").lower() == user_email.lower():
                    attendee["responseStatus"] = response
                    break

            event["attendees"] = attendees

            self.service.events().update(
                calendarId=calendar_id, eventId=event_id, body=event
            ).execute()

            return True
        except HttpError as e:
            raise RuntimeError(f"Calendar API error: {e}")

    def get_upcoming_events(
        self,
        days: int = 7,
        max_results: int = 50,
        calendar_id: str = "primary",
    ) -> list[dict]:
        """
        Get upcoming events for the next N days.

        Args:
            days: Number of days to look ahead
            max_results: Maximum events to return
            calendar_id: The calendar ID

        Returns:
            List of events
        """
        now = datetime.now()
        end = now + timedelta(days=days)
        return self.list_events(
            calendar_id=calendar_id,
            time_min=now,
            time_max=end,
            max_results=max_results,
        )

    def get_today_events(self) -> list[dict]:
        """Get events for today (local time)."""
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        return self.list_events(time_min=start_of_day, time_max=end_of_day)

    def get_week_events(self) -> list[dict]:
        """Get events for this week (next 7 days)."""
        return self.get_upcoming_events(days=7)

    def find_event_by_id(self, event_id: str) -> Optional[dict]:
        """
        Find an event by ID, searching across all calendars.

        Args:
            event_id: The event ID to find

        Returns:
            Event dictionary or None
        """
        calendars = self.list_calendars()
        for cal in calendars:
            event = self.get_event(event_id, calendar_id=cal["id"])
            if event:
                return event
        return None
