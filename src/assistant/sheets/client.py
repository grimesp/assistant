"""Google Sheets API client wrapper."""

from typing import Any, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..auth import get_credentials


class SheetsClient:
    """Wrapper class for Google Sheets API operations."""

    def __init__(self):
        """Initialize the Sheets client."""
        self._sheets_service = None
        self._drive_service = None

    @property
    def sheets_service(self):
        """Get or create the Sheets API service."""
        if self._sheets_service is None:
            creds = get_credentials()
            if creds is None:
                raise RuntimeError("Not authenticated. Run 'assistant auth login' first.")
            self._sheets_service = build("sheets", "v4", credentials=creds)
        return self._sheets_service

    @property
    def drive_service(self):
        """Get or create the Drive API service (for listing spreadsheets)."""
        if self._drive_service is None:
            creds = get_credentials()
            if creds is None:
                raise RuntimeError("Not authenticated. Run 'assistant auth login' first.")
            self._drive_service = build("drive", "v3", credentials=creds)
        return self._drive_service

    def list_spreadsheets(self, max_results: int = 20, query: Optional[str] = None) -> list[dict]:
        """
        List spreadsheets the user has access to.

        Args:
            max_results: Maximum number of spreadsheets to return
            query: Optional search query to filter by name

        Returns:
            List of spreadsheet dictionaries with id, name, modifiedTime, webViewLink
        """
        try:
            q_parts = ["mimeType='application/vnd.google-apps.spreadsheet'"]
            if query:
                q_parts.append(f"name contains '{query}'")
            q = " and ".join(q_parts)

            response = (
                self.drive_service.files()
                .list(
                    q=q,
                    pageSize=max_results,
                    fields="files(id, name, modifiedTime, webViewLink, owners)",
                    orderBy="modifiedTime desc",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )

            files = response.get("files", [])
            result = []
            for f in files:
                owners = f.get("owners", [])
                owner_email = owners[0].get("emailAddress", "") if owners else ""
                result.append({
                    "id": f["id"],
                    "name": f.get("name", ""),
                    "modified_time": f.get("modifiedTime", ""),
                    "web_view_link": f.get("webViewLink", ""),
                    "owner": owner_email,
                })

            return result
        except HttpError as e:
            raise RuntimeError(f"Drive API error: {e}")

    def get_spreadsheet(self, spreadsheet_id: str) -> dict:
        """
        Get spreadsheet metadata.

        Args:
            spreadsheet_id: The spreadsheet ID

        Returns:
            Spreadsheet dictionary with metadata and sheet info
        """
        try:
            spreadsheet = (
                self.sheets_service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id)
                .execute()
            )

            sheets = []
            for sheet in spreadsheet.get("sheets", []):
                props = sheet.get("properties", {})
                sheets.append({
                    "sheet_id": props.get("sheetId"),
                    "title": props.get("title", ""),
                    "index": props.get("index", 0),
                    "row_count": props.get("gridProperties", {}).get("rowCount", 0),
                    "column_count": props.get("gridProperties", {}).get("columnCount", 0),
                })

            return {
                "id": spreadsheet.get("spreadsheetId"),
                "title": spreadsheet.get("properties", {}).get("title", ""),
                "locale": spreadsheet.get("properties", {}).get("locale", ""),
                "time_zone": spreadsheet.get("properties", {}).get("timeZone", ""),
                "web_view_link": spreadsheet.get("spreadsheetUrl", ""),
                "sheets": sheets,
            }
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Spreadsheet not found: {spreadsheet_id}")
            raise RuntimeError(f"Sheets API error: {e}")

    def read_range(
        self,
        spreadsheet_id: str,
        range_name: str,
        value_render_option: str = "FORMATTED_VALUE",
    ) -> list[list[Any]]:
        """
        Read cell values from a range.

        Args:
            spreadsheet_id: The spreadsheet ID
            range_name: A1 notation range (e.g., "Sheet1!A1:C10" or "A1:C10")
            value_render_option: How values should be rendered (FORMATTED_VALUE, UNFORMATTED_VALUE, FORMULA)

        Returns:
            2D list of cell values
        """
        try:
            result = (
                self.sheets_service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueRenderOption=value_render_option,
                )
                .execute()
            )

            return result.get("values", [])
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Spreadsheet not found: {spreadsheet_id}")
            raise RuntimeError(f"Sheets API error: {e}")

    def write_range(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> dict:
        """
        Write values to a range.

        Args:
            spreadsheet_id: The spreadsheet ID
            range_name: A1 notation range (e.g., "Sheet1!A1:C10")
            values: 2D list of values to write
            value_input_option: How input should be interpreted (RAW, USER_ENTERED)

        Returns:
            Update result with updated range and cell counts
        """
        try:
            body = {"values": values}
            result = (
                self.sheets_service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body=body,
                )
                .execute()
            )

            return {
                "updated_range": result.get("updatedRange", ""),
                "updated_rows": result.get("updatedRows", 0),
                "updated_columns": result.get("updatedColumns", 0),
                "updated_cells": result.get("updatedCells", 0),
            }
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Spreadsheet not found: {spreadsheet_id}")
            raise RuntimeError(f"Sheets API error: {e}")

    def append_rows(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> dict:
        """
        Append rows to a range.

        Args:
            spreadsheet_id: The spreadsheet ID
            range_name: A1 notation range to append after (e.g., "Sheet1" or "Sheet1!A:Z")
            values: 2D list of row values to append
            value_input_option: How input should be interpreted (RAW, USER_ENTERED)

        Returns:
            Append result with updated range info
        """
        try:
            body = {"values": values}
            result = (
                self.sheets_service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    insertDataOption="INSERT_ROWS",
                    body=body,
                )
                .execute()
            )

            updates = result.get("updates", {})
            return {
                "updated_range": updates.get("updatedRange", ""),
                "updated_rows": updates.get("updatedRows", 0),
                "updated_columns": updates.get("updatedColumns", 0),
                "updated_cells": updates.get("updatedCells", 0),
            }
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Spreadsheet not found: {spreadsheet_id}")
            raise RuntimeError(f"Sheets API error: {e}")

    def clear_range(self, spreadsheet_id: str, range_name: str) -> dict:
        """
        Clear values from a range.

        Args:
            spreadsheet_id: The spreadsheet ID
            range_name: A1 notation range to clear

        Returns:
            Result with cleared range
        """
        try:
            result = (
                self.sheets_service.spreadsheets()
                .values()
                .clear(spreadsheetId=spreadsheet_id, range=range_name, body={})
                .execute()
            )

            return {"cleared_range": result.get("clearedRange", "")}
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Spreadsheet not found: {spreadsheet_id}")
            raise RuntimeError(f"Sheets API error: {e}")

    def create_spreadsheet(self, title: str) -> dict:
        """
        Create a new spreadsheet.

        Args:
            title: The title for the new spreadsheet

        Returns:
            Created spreadsheet info with id and url
        """
        try:
            spreadsheet = (
                self.sheets_service.spreadsheets()
                .create(body={"properties": {"title": title}})
                .execute()
            )

            return {
                "id": spreadsheet.get("spreadsheetId"),
                "title": spreadsheet.get("properties", {}).get("title", ""),
                "web_view_link": spreadsheet.get("spreadsheetUrl", ""),
            }
        except HttpError as e:
            raise RuntimeError(f"Sheets API error: {e}")

    def list_sheets(self, spreadsheet_id: str) -> list[dict]:
        """
        List all sheets in a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID

        Returns:
            List of sheet dictionaries
        """
        spreadsheet = self.get_spreadsheet(spreadsheet_id)
        return spreadsheet.get("sheets", [])

    def add_sheet(self, spreadsheet_id: str, title: str) -> dict:
        """
        Add a new sheet to a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID
            title: The title for the new sheet

        Returns:
            Created sheet info
        """
        try:
            request = {
                "requests": [{"addSheet": {"properties": {"title": title}}}]
            }
            response = (
                self.sheets_service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=request)
                .execute()
            )

            reply = response.get("replies", [{}])[0]
            props = reply.get("addSheet", {}).get("properties", {})

            return {
                "sheet_id": props.get("sheetId"),
                "title": props.get("title", ""),
                "index": props.get("index", 0),
            }
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Spreadsheet not found: {spreadsheet_id}")
            raise RuntimeError(f"Sheets API error: {e}")

    def delete_sheet(self, spreadsheet_id: str, sheet_id: int) -> bool:
        """
        Delete a sheet from a spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet ID
            sheet_id: The sheet ID (not the title)

        Returns:
            True if successful
        """
        try:
            request = {"requests": [{"deleteSheet": {"sheetId": sheet_id}}]}
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=request
            ).execute()
            return True
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Spreadsheet not found: {spreadsheet_id}")
            raise RuntimeError(f"Sheets API error: {e}")

    def rename_sheet(self, spreadsheet_id: str, sheet_id: int, title: str) -> bool:
        """
        Rename a sheet.

        Args:
            spreadsheet_id: The spreadsheet ID
            sheet_id: The sheet ID (not the title)
            title: The new title

        Returns:
            True if successful
        """
        try:
            request = {
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {"sheetId": sheet_id, "title": title},
                            "fields": "title",
                        }
                    }
                ]
            }
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=request
            ).execute()
            return True
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Spreadsheet not found: {spreadsheet_id}")
            raise RuntimeError(f"Sheets API error: {e}")
