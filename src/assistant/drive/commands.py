"""Google Drive CLI commands."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from ..auth import is_authenticated
from ..utils.display import console, display_error, display_success
from .client import DriveClient, EXPORT_MIME_TYPES

app = typer.Typer(help="Google Drive commands")


def require_auth():
    """Check authentication and exit if not authenticated."""
    if not is_authenticated():
        display_error("Not authenticated. Run 'assistant auth login' first.")
        raise typer.Exit(1)


def format_file_list(files: list[dict]) -> Table:
    """Format a list of files as a Rich table."""
    table = Table(show_header=True, header_style="bold blue", box=None)
    table.add_column("ID", style="dim", width=35, overflow="fold")
    table.add_column("Name", width=30, overflow="ellipsis")
    table.add_column("Type", width=12, overflow="ellipsis")
    table.add_column("Size", width=10, justify="right")
    table.add_column("Modified", width=12)

    for f in files:
        # Format MIME type for display
        mime = f.get("mime_type", "")
        if mime.startswith("application/vnd.google-apps."):
            type_display = mime.replace("application/vnd.google-apps.", "G-")
        elif "/" in mime:
            type_display = mime.split("/")[-1][:15]
        else:
            type_display = mime[:15]

        # Format size
        size = f.get("size")
        if size is None:
            size_str = "-"
        elif size > 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        elif size > 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} B"

        # Format modified time
        modified = f.get("modified_time", "")
        if modified:
            try:
                dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
                modified = dt.strftime("%b %d, %Y")
            except (ValueError, AttributeError):
                modified = modified[:10]

        table.add_row(
            f.get("id", ""),
            f.get("name", "")[:40],
            type_display,
            size_str,
            modified,
        )

    return table


def format_file_detail(file: dict) -> Panel:
    """Format file metadata as a Rich panel."""
    lines = [
        f"[bold blue]Name:[/bold blue] {file.get('name', '')}",
        f"[bold blue]ID:[/bold blue] {file.get('id', '')}",
        f"[bold blue]Type:[/bold blue] {file.get('mime_type', '')}",
    ]

    size = file.get("size")
    if size is not None:
        if size > 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        elif size > 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} B"
        lines.append(f"[bold blue]Size:[/bold blue] {size_str}")
    else:
        lines.append("[bold blue]Size:[/bold blue] [dim](Google Workspace file)[/dim]")

    if file.get("owner"):
        lines.append(f"[bold blue]Owner:[/bold blue] {file['owner']}")

    if file.get("created_time"):
        try:
            dt = datetime.fromisoformat(file["created_time"].replace("Z", "+00:00"))
            lines.append(f"[bold blue]Created:[/bold blue] {dt.strftime('%B %d, %Y at %I:%M %p')}")
        except (ValueError, AttributeError):
            lines.append(f"[bold blue]Created:[/bold blue] {file['created_time']}")

    if file.get("modified_time"):
        try:
            dt = datetime.fromisoformat(file["modified_time"].replace("Z", "+00:00"))
            lines.append(f"[bold blue]Modified:[/bold blue] {dt.strftime('%B %d, %Y at %I:%M %p')}")
        except (ValueError, AttributeError):
            lines.append(f"[bold blue]Modified:[/bold blue] {file['modified_time']}")

    if file.get("web_view_link"):
        lines.append(f"[bold blue]URL:[/bold blue] {file['web_view_link']}")

    # Show export formats for Google Workspace files
    mime_type = file.get("mime_type", "")
    if mime_type in EXPORT_MIME_TYPES:
        export_info = EXPORT_MIME_TYPES[mime_type]
        formats = ", ".join(export_info["formats"].keys())
        lines.append(f"\n[bold blue]Export formats:[/bold blue] {formats}")
        default_ext = export_info["extension"].lstrip(".")
        lines.append(f"[bold blue]Default export:[/bold blue] {default_ext}")

    content = "\n".join(lines)

    return Panel(
        content,
        title="[bold]File Info[/bold]",
        border_style="blue",
    )


@app.command("list")
def list_files(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of files to show"),
):
    """List recent files from Google Drive."""
    require_auth()

    client = DriveClient()
    try:
        files = client.list_files(query=query, max_results=limit)

        if not files:
            console.print("No files found.")
            return

        table = format_file_list(files)
        console.print(table)
        console.print(f"\n[dim]{len(files)} files[/dim]")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("info")
def file_info(
    file_id: str = typer.Argument(..., help="File ID or Google Drive URL"),
):
    """Show file metadata."""
    require_auth()

    client = DriveClient()
    try:
        metadata = client.get_file_metadata(file_id)
        panel = format_file_detail(metadata)
        console.print(panel)
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("download")
def download_file(
    file_id: str = typer.Argument(..., help="File ID or Google Drive URL"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output path or directory"),
    format: Optional[str] = typer.Option(
        None, "--format", "-f", help="Export format for Google Workspace files (pdf, csv, xlsx, docx, etc.)"
    ),
):
    """Download a file from Google Drive.

    For regular files, downloads directly. For Google Workspace files
    (Docs, Sheets, Slides), exports to the specified format.

    Examples:
        assistant drive download 1ABC123xyz
        assistant drive download "https://drive.google.com/file/d/1ABC123xyz/view"
        assistant drive download 1ABC123xyz -o ./downloads/
        assistant drive download 1ABC123xyz -f xlsx
    """
    require_auth()

    client = DriveClient()
    try:
        output_path = str(output) if output else None
        downloaded_path = client.download_file(file_id, output_path, export_format=format)
        display_success(f"Downloaded: {downloaded_path}")
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)
