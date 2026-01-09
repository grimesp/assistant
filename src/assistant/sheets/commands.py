"""Google Sheets CLI commands."""

import csv
from pathlib import Path
from typing import Optional

import typer

from ..auth import is_authenticated
from ..utils.display import (
    console,
    display_error,
    display_success,
    confirm,
    format_spreadsheet_list,
    format_spreadsheet_detail,
    format_sheet_data,
)
from .client import SheetsClient

app = typer.Typer(help="Google Sheets commands")


def require_auth():
    """Check authentication and exit if not authenticated."""
    if not is_authenticated():
        display_error("Not authenticated. Run 'assistant auth login' first.")
        raise typer.Exit(1)


@app.command("list")
def list_spreadsheets(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of spreadsheets to show"),
):
    """List recent spreadsheets."""
    require_auth()

    client = SheetsClient()
    try:
        spreadsheets = client.list_spreadsheets(max_results=limit)

        if not spreadsheets:
            console.print("No spreadsheets found.")
            return

        table = format_spreadsheet_list(spreadsheets)
        console.print(table)
        console.print(f"\n[dim]{len(spreadsheets)} spreadsheets[/dim]")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("show")
def show_spreadsheet(
    spreadsheet_id: str = typer.Argument(..., help="Spreadsheet ID"),
):
    """Show spreadsheet details and sheets."""
    require_auth()

    client = SheetsClient()
    try:
        spreadsheet = client.get_spreadsheet(spreadsheet_id)
        panel = format_spreadsheet_detail(spreadsheet)
        console.print(panel)
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("read")
def read_range(
    spreadsheet_id: str = typer.Argument(..., help="Spreadsheet ID"),
    range_name: str = typer.Argument(..., help="Range in A1 notation (e.g., 'Sheet1!A1:C10')"),
    formulas: bool = typer.Option(False, "--formulas", "-f", help="Show formulas instead of values"),
):
    """Read cell data from a spreadsheet."""
    require_auth()

    client = SheetsClient()
    try:
        render_option = "FORMULA" if formulas else "FORMATTED_VALUE"
        values = client.read_range(spreadsheet_id, range_name, value_render_option=render_option)

        if not values:
            console.print("No data found in range.")
            return

        table = format_sheet_data(values)
        console.print(table)
        console.print(f"\n[dim]{len(values)} rows[/dim]")
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("write")
def write_range(
    spreadsheet_id: str = typer.Argument(..., help="Spreadsheet ID"),
    range_name: str = typer.Argument(..., help="Range in A1 notation (e.g., 'Sheet1!A1')"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Single value or comma-separated row"),
    csv_file: Optional[Path] = typer.Option(None, "--csv", help="CSV file to write"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Write values as-is (no parsing)"),
):
    """Write data to a spreadsheet."""
    require_auth()

    if not value and not csv_file:
        display_error("Either --value or --csv must be provided.")
        raise typer.Exit(1)

    client = SheetsClient()
    try:
        if csv_file:
            if not csv_file.exists():
                display_error(f"File not found: {csv_file}")
                raise typer.Exit(1)

            with open(csv_file, newline="") as f:
                reader = csv.reader(f)
                values = list(reader)
        else:
            # Parse comma-separated value as single row
            values = [[v.strip() for v in value.split(",")]]

        input_option = "RAW" if raw else "USER_ENTERED"
        result = client.write_range(spreadsheet_id, range_name, values, value_input_option=input_option)

        display_success(
            f"Updated {result['updated_cells']} cells in {result['updated_range']}"
        )
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("append")
def append_rows(
    spreadsheet_id: str = typer.Argument(..., help="Spreadsheet ID"),
    range_name: str = typer.Argument(..., help="Range to append to (e.g., 'Sheet1' or 'Sheet1!A:Z')"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Comma-separated row values"),
    csv_file: Optional[Path] = typer.Option(None, "--csv", help="CSV file to append"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Write values as-is (no parsing)"),
):
    """Append rows to a spreadsheet."""
    require_auth()

    if not value and not csv_file:
        display_error("Either --value or --csv must be provided.")
        raise typer.Exit(1)

    client = SheetsClient()
    try:
        if csv_file:
            if not csv_file.exists():
                display_error(f"File not found: {csv_file}")
                raise typer.Exit(1)

            with open(csv_file, newline="") as f:
                reader = csv.reader(f)
                values = list(reader)
        else:
            values = [[v.strip() for v in value.split(",")]]

        input_option = "RAW" if raw else "USER_ENTERED"
        result = client.append_rows(spreadsheet_id, range_name, values, value_input_option=input_option)

        display_success(
            f"Appended {result['updated_rows']} rows ({result['updated_cells']} cells)"
        )
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("clear")
def clear_range(
    spreadsheet_id: str = typer.Argument(..., help="Spreadsheet ID"),
    range_name: str = typer.Argument(..., help="Range to clear (e.g., 'Sheet1!A1:C10')"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clear data from a range."""
    require_auth()

    if not yes:
        if not confirm(f"Clear all data in {range_name}?"):
            console.print("Cancelled.")
            return

    client = SheetsClient()
    try:
        result = client.clear_range(spreadsheet_id, range_name)
        display_success(f"Cleared range: {result['cleared_range']}")
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("create")
def create_spreadsheet(
    title: str = typer.Option(..., "--title", "-t", help="Spreadsheet title"),
):
    """Create a new spreadsheet."""
    require_auth()

    client = SheetsClient()
    try:
        result = client.create_spreadsheet(title)
        display_success(f"Created spreadsheet: {result['title']}")
        console.print(f"ID: {result['id']}")
        console.print(f"URL: {result['web_view_link']}")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("add-sheet")
def add_sheet(
    spreadsheet_id: str = typer.Argument(..., help="Spreadsheet ID"),
    title: str = typer.Option(..., "--title", "-t", help="Sheet title"),
):
    """Add a new sheet to a spreadsheet."""
    require_auth()

    client = SheetsClient()
    try:
        result = client.add_sheet(spreadsheet_id, title)
        display_success(f"Created sheet: {result['title']} (ID: {result['sheet_id']})")
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("delete-sheet")
def delete_sheet(
    spreadsheet_id: str = typer.Argument(..., help="Spreadsheet ID"),
    sheet_id: int = typer.Argument(..., help="Sheet ID (numeric, not title)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a sheet from a spreadsheet."""
    require_auth()

    if not yes:
        if not confirm(f"Delete sheet {sheet_id}?"):
            console.print("Cancelled.")
            return

    client = SheetsClient()
    try:
        client.delete_sheet(spreadsheet_id, sheet_id)
        display_success(f"Deleted sheet: {sheet_id}")
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("rename-sheet")
def rename_sheet(
    spreadsheet_id: str = typer.Argument(..., help="Spreadsheet ID"),
    sheet_id: int = typer.Argument(..., help="Sheet ID (numeric, not title)"),
    title: str = typer.Option(..., "--title", "-t", help="New sheet title"),
):
    """Rename a sheet in a spreadsheet."""
    require_auth()

    client = SheetsClient()
    try:
        client.rename_sheet(spreadsheet_id, sheet_id, title)
        display_success(f"Renamed sheet {sheet_id} to: {title}")
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)
