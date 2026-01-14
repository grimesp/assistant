"""Gmail CLI commands."""

from pathlib import Path
from typing import Optional

import typer

from ..auth import is_authenticated
from ..utils.display import (
    console,
    display_error,
    display_success,
    display_warning,
    format_attachments,
    format_drafts,
    format_email_detail,
    format_email_list,
    format_labels,
    open_editor,
    confirm,
)
from .client import GmailClient

app = typer.Typer(help="Gmail commands")


def require_auth():
    """Check authentication and exit if not authenticated."""
    if not is_authenticated():
        display_error("Not authenticated. Run 'assistant auth login' first.")
        raise typer.Exit(1)


@app.command("list")
def list_messages(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of messages to show"),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="Filter by label"),
):
    """List recent emails."""
    require_auth()

    client = GmailClient()
    try:
        label_ids = [label] if label else None
        messages = client.list_messages(max_results=limit, label_ids=label_ids)

        if not messages:
            console.print("No messages found.")
            return

        table = format_email_list(messages)
        console.print(table)
        console.print(f"\n[dim]{len(messages)} messages[/dim]")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("search")
def search_messages(
    query: str = typer.Argument(..., help="Gmail search query"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of results"),
):
    """Search emails using Gmail query syntax."""
    require_auth()

    client = GmailClient()
    try:
        messages = client.search(query=query, max_results=limit)

        if not messages:
            console.print(f"No messages found for: {query}")
            return

        table = format_email_list(messages)
        console.print(table)
        console.print(f"\n[dim]{len(messages)} results for '{query}'[/dim]")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("read")
def read_message(
    message_id: str = typer.Argument(..., help="Message ID to read"),
):
    """Read a specific email."""
    require_auth()

    client = GmailClient()
    try:
        message = client.get_message(message_id)

        if not message:
            display_error(f"Message not found: {message_id}")
            raise typer.Exit(1)

        panel = format_email_detail(message)
        console.print(panel)

        # Mark as read
        client.mark_as_read(message_id)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("labels")
def list_labels():
    """List all Gmail labels."""
    require_auth()

    client = GmailClient()
    try:
        labels = client.list_labels()
        table = format_labels(labels)
        console.print(table)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("label-create")
def create_label(
    name: str = typer.Argument(..., help="Label name to create"),
):
    """Create a new Gmail label."""
    require_auth()

    client = GmailClient()
    try:
        label = client.create_label(name)
        display_success(f"Created label: {label['name']}")
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("label-apply")
def apply_label(
    label: str = typer.Argument(..., help="Label to apply"),
    query: str = typer.Option(..., "--query", "-q", help="Gmail search query to match emails"),
    limit: int = typer.Option(500, "--limit", "-n", help="Maximum emails to process"),
):
    """Apply a label to emails matching a search query."""
    require_auth()

    client = GmailClient()
    try:
        # Get the label ID
        label_id = client.get_label_id(label)
        if not label_id:
            display_error(f"Label not found: {label}")
            raise typer.Exit(1)

        # Search for matching emails
        messages = client.search(query, max_results=limit)
        if not messages:
            console.print(f"No emails found matching: {query}")
            return

        # Apply label to each
        count = 0
        for msg in messages:
            client.modify_labels(msg["id"], add_labels=[label_id])
            count += 1

        display_success(f"Applied '{label}' to {count} emails.")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("attachments")
def list_attachments(
    message_id: str = typer.Argument(..., help="Message ID"),
    download: Optional[str] = typer.Option(
        None, "--download", "-d", help="Download to this directory"
    ),
):
    """List or download attachments from an email."""
    require_auth()

    client = GmailClient()
    try:
        message = client.get_message(message_id)

        if not message:
            display_error(f"Message not found: {message_id}")
            raise typer.Exit(1)

        attachments = message.get("attachments", [])

        if not attachments:
            console.print("No attachments in this message.")
            return

        if download:
            download_dir = Path(download)
            download_dir.mkdir(parents=True, exist_ok=True)

            for att in attachments:
                if att.get("id"):
                    path = client.get_attachment(
                        message_id=message_id,
                        attachment_id=att["id"],
                        filename=att["filename"],
                        download_dir=str(download_dir),
                    )
                    display_success(f"Downloaded: {path}")
        else:
            table = format_attachments(attachments)
            console.print(table)
            console.print(
                f"\n[dim]Use --download DIR to download attachments[/dim]"
            )
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("compose")
def compose_message(
    to: str = typer.Option(..., "--to", "-t", help="Recipient email"),
    subject: str = typer.Option(..., "--subject", "-s", help="Email subject"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Email body"),
    cc: Optional[str] = typer.Option(None, "--cc", help="CC recipients"),
    attach: Optional[list[str]] = typer.Option(None, "--attach", "-a", help="Files to attach"),
    html: bool = typer.Option(False, "--html", help="Send body as HTML"),
):
    """Compose and send a new email."""
    require_auth()

    # If no body provided, open editor
    if body is None:
        body = open_editor()
        if body is None:
            display_warning("Email cancelled (empty body).")
            return

    client = GmailClient()
    try:
        result = client.send_message(
            to=to,
            subject=subject,
            body=body,
            cc=cc or "",
            attachments=attach,
            is_html=html,
        )
        display_success(f"Email sent! ID: {result['id']}")
    except FileNotFoundError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("reply")
def reply_to_message(
    message_id: str = typer.Argument(..., help="Message ID to reply to"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Reply body"),
    reply_all: bool = typer.Option(False, "--all", "-a", help="Reply to all"),
):
    """Reply to an email."""
    require_auth()

    client = GmailClient()

    # Get original message for context
    try:
        original = client.get_message(message_id)
        if not original:
            display_error(f"Message not found: {message_id}")
            raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)

    # If no body provided, open editor with quote
    if body is None:
        quote = f"\n\nOn {original['date']}, {original['from']} wrote:\n> "
        quote += original.get("body", "")[:500].replace("\n", "\n> ")
        body = open_editor(f"\n{quote}")
        if body is None:
            display_warning("Reply cancelled (empty body).")
            return

    try:
        result = client.reply(message_id=message_id, body=body, reply_all=reply_all)
        display_success(f"Reply sent! ID: {result['id']}")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("forward")
def forward_message(
    message_id: str = typer.Argument(..., help="Message ID to forward"),
    to: str = typer.Option(..., "--to", "-t", help="Recipient email"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Additional message"),
):
    """Forward an email."""
    require_auth()

    # If no body provided, open editor
    if body is None:
        body = open_editor("Add a message (optional):\n\n")
        if body and body.startswith("Add a message"):
            body = ""

    client = GmailClient()
    try:
        result = client.forward(message_id=message_id, to=to, body=body or "")
        display_success(f"Message forwarded! ID: {result['id']}")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("drafts")
def list_drafts():
    """List all drafts."""
    require_auth()

    client = GmailClient()
    try:
        drafts = client.list_drafts()

        if not drafts:
            console.print("No drafts found.")
            return

        table = format_drafts(drafts)
        console.print(table)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("draft")
def create_draft(
    to: str = typer.Option(..., "--to", "-t", help="Recipient email"),
    subject: str = typer.Option(..., "--subject", "-s", help="Email subject"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Email body"),
    cc: Optional[str] = typer.Option(None, "--cc", help="CC recipients"),
):
    """Create a new draft."""
    require_auth()

    # If no body provided, open editor
    if body is None:
        body = open_editor()
        if body is None:
            display_warning("Draft cancelled (empty body).")
            return

    client = GmailClient()
    try:
        result = client.create_draft(
            to=to,
            subject=subject,
            body=body,
            cc=cc or "",
        )
        display_success(f"Draft created! ID: {result['id']}")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("send-draft")
def send_draft(
    draft_id: str = typer.Argument(..., help="Draft ID to send"),
):
    """Send a draft."""
    require_auth()

    client = GmailClient()
    try:
        result = client.send_draft(draft_id)
        display_success(f"Draft sent! Message ID: {result['id']}")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("delete-draft")
def delete_draft(
    draft_id: str = typer.Argument(..., help="Draft ID to delete"),
):
    """Delete a draft."""
    require_auth()

    if not confirm(f"Delete draft {draft_id}?"):
        console.print("Cancelled.")
        return

    client = GmailClient()
    try:
        client.delete_draft(draft_id)
        display_success("Draft deleted.")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("trash")
def trash_message(
    message_ids: list[str] = typer.Argument(..., help="Message ID(s) to trash"),
):
    """Move message(s) to trash."""
    require_auth()

    client = GmailClient()
    count = 0
    for message_id in message_ids:
        try:
            client.trash_message(message_id)
            count += 1
        except RuntimeError as e:
            display_error(f"Failed to trash {message_id}: {e}")
    display_success(f"Moved {count} message(s) to trash.")


@app.command("delete")
def delete_message(
    message_id: str = typer.Argument(..., help="Message ID to delete"),
):
    """Permanently delete a message."""
    require_auth()

    if not confirm(f"Permanently delete message {message_id}? This cannot be undone."):
        console.print("Cancelled.")
        return

    client = GmailClient()
    try:
        client.delete_message(message_id)
        display_success("Message permanently deleted.")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("mark-read")
def mark_read(
    message_id: Optional[str] = typer.Argument(None, help="Message ID"),
    all_unread: bool = typer.Option(False, "--all-unread", help="Mark all unread messages as read"),
):
    """Mark a message as read."""
    require_auth()

    if not message_id and not all_unread:
        display_error("Provide a message ID or use --all-unread.")
        raise typer.Exit(1)

    client = GmailClient()
    try:
        if all_unread:
            messages = client.search("is:unread", max_results=500)
            if not messages:
                console.print("No unread messages found.")
                return
            count = 0
            for msg in messages:
                client.mark_as_read(msg["id"])
                count += 1
            display_success(f"Marked {count} messages as read.")
        else:
            client.mark_as_read(message_id)
            display_success("Message marked as read.")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("mark-unread")
def mark_unread(
    message_id: str = typer.Argument(..., help="Message ID"),
):
    """Mark a message as unread."""
    require_auth()

    client = GmailClient()
    try:
        client.mark_as_unread(message_id)
        display_success("Message marked as unread.")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("label")
def modify_labels(
    message_id: str = typer.Argument(..., help="Message ID"),
    add: Optional[list[str]] = typer.Option(None, "--add", help="Labels to add"),
    remove: Optional[list[str]] = typer.Option(None, "--remove", help="Labels to remove"),
):
    """Add or remove labels from a message."""
    require_auth()

    if not add and not remove:
        display_error("Specify --add or --remove labels.")
        raise typer.Exit(1)

    client = GmailClient()
    try:
        client.modify_labels(message_id, add_labels=add, remove_labels=remove)
        display_success("Labels updated.")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("archive")
def archive_message(
    message_ids: list[str] | None = typer.Argument(
        None, help="Message ID(s) to archive"
    ),
    all_inbox: bool = typer.Option(
        False, "--all-inbox", help="Archive all messages in inbox"
    ),
):
    """Archive message(s) (remove from inbox)."""
    require_auth()

    if not message_ids and not all_inbox:
        display_error("Provide message ID(s) or use --all-inbox.")
        raise typer.Exit(1)

    client = GmailClient()
    try:
        if all_inbox:
            messages = client.list_messages(max_results=500, label_ids=["INBOX"])
            if not messages:
                console.print("No messages in inbox.")
                return
            count = 0
            for msg in messages:
                client.archive(msg["id"])
                count += 1
            display_success(f"Archived {count} messages.")
        else:
            count = 0
            for message_id in message_ids:
                client.archive(message_id)
                count += 1
            display_success(f"Archived {count} message(s).")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("clear-inbox")
def clear_inbox(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Archive read, non-starred messages from inbox.

    Safety: Leaves unread and starred messages in inbox.
    Use 'mark-read --all-unread' first if you want to clear everything.
    """
    require_auth()

    client = GmailClient()
    try:
        # Get all inbox messages
        messages = client.list_messages(max_results=500, label_ids=["INBOX"])
        if not messages:
            console.print("Inbox is already empty.")
            return

        # Filter to only read, non-starred messages
        to_archive = []
        skipped_unread = 0
        skipped_starred = 0

        for msg in messages:
            labels = msg.get("labels", [])
            if msg.get("unread", False):
                skipped_unread += 1
            elif "STARRED" in labels:
                skipped_starred += 1
            else:
                to_archive.append(msg)

        if not to_archive:
            console.print(f"No messages to archive. Skipped {skipped_unread} unread, {skipped_starred} starred.")
            return

        if not yes:
            skip_msg = ""
            if skipped_unread or skipped_starred:
                skip_msg = f" (skipping {skipped_unread} unread, {skipped_starred} starred)"
            if not confirm(f"Archive {len(to_archive)} read messages?{skip_msg}"):
                console.print("Cancelled.")
                return

        for msg in to_archive:
            client.archive(msg["id"])

        display_success(f"Archived {len(to_archive)} messages. Skipped {skipped_unread} unread, {skipped_starred} starred.")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("filters")
def list_filters():
    """List all Gmail filters."""
    require_auth()

    client = GmailClient()
    try:
        filters = client.list_filters()

        if not filters:
            console.print("No filters found.")
            return

        from rich.table import Table
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("ID", style="dim", width=20)
        table.add_column("Criteria", width=35)
        table.add_column("Actions", width=35)

        for f in filters:
            # Build criteria string
            criteria_parts = []
            if f["from"]:
                criteria_parts.append(f"from:{f['from']}")
            if f["to"]:
                criteria_parts.append(f"to:{f['to']}")
            if f["subject"]:
                criteria_parts.append(f"subject:{f['subject']}")
            if f["query"]:
                criteria_parts.append(f["query"])
            criteria_str = " ".join(criteria_parts) or "(none)"

            # Build actions string
            action_parts = []
            if "INBOX" in f["remove_labels"]:
                action_parts.append("Skip Inbox")
            if "UNREAD" in f["remove_labels"]:
                action_parts.append("Mark Read")
            if "STARRED" in f["add_labels"]:
                action_parts.append("Star")
            if "TRASH" in f["add_labels"]:
                action_parts.append("Trash")
            if f["forward"]:
                action_parts.append(f"Forward to {f['forward']}")
            # Show other labels
            other_add = [l for l in f["add_labels"] if l not in ["STARRED", "TRASH", "IMPORTANT"]]
            other_remove = [l for l in f["remove_labels"] if l not in ["INBOX", "UNREAD", "SPAM", "IMPORTANT"]]
            if other_add:
                action_parts.append(f"+{','.join(other_add)}")
            if other_remove:
                action_parts.append(f"-{','.join(other_remove)}")
            action_str = ", ".join(action_parts) or "(none)"

            table.add_row(f["id"], criteria_str, action_str)

        console.print(table)
        console.print(f"\n[dim]{len(filters)} filters[/dim]")
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("filter-create")
def create_filter(
    from_addr: Optional[str] = typer.Option(None, "--from", "-f", help="Filter by sender"),
    to_addr: Optional[str] = typer.Option(None, "--to", "-t", help="Filter by recipient"),
    subject: Optional[str] = typer.Option(None, "--subject", "-s", help="Filter by subject"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Gmail search query"),
    archive: bool = typer.Option(False, "--archive", help="Skip inbox (archive)"),
    mark_read: bool = typer.Option(False, "--mark-read", help="Mark as read"),
    star: bool = typer.Option(False, "--star", help="Star the message"),
    trash: bool = typer.Option(False, "--trash", help="Move to trash"),
    add_label: Optional[list[str]] = typer.Option(None, "--add-label", "-a", help="Add label"),
    remove_label: Optional[list[str]] = typer.Option(None, "--remove-label", "-r", help="Remove label"),
    forward_to: Optional[str] = typer.Option(None, "--forward", help="Forward to email"),
    category: Optional[str] = typer.Option(None, "--category", help="Category (primary, social, promotions, updates, forums)"),
):
    """Create a Gmail filter.

    Examples:
        assistant gmail filter-create --from linkedin.com --archive
        assistant gmail filter-create --from newsletter@example.com --mark-read --archive
        assistant gmail filter-create --subject "urgent" --star
    """
    require_auth()

    if not any([from_addr, to_addr, subject, query]):
        display_error("Specify at least one criteria: --from, --to, --subject, or --query")
        raise typer.Exit(1)

    if not any([archive, mark_read, star, trash, add_label, remove_label, forward_to, category]):
        display_error("Specify at least one action: --archive, --mark-read, --star, --trash, --add-label, --remove-label, --forward, or --category")
        raise typer.Exit(1)

    client = GmailClient()
    try:
        result = client.create_filter(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=subject,
            query=query,
            add_labels=add_label,
            remove_labels=remove_label,
            forward_to=forward_to,
            mark_read=mark_read,
            star=star,
            archive=archive,
            trash=trash,
            category=category,
        )
        display_success(f"Filter created: {result['id']}")

        # Show what the filter does
        criteria_parts = []
        if from_addr:
            criteria_parts.append(f"from:{from_addr}")
        if to_addr:
            criteria_parts.append(f"to:{to_addr}")
        if subject:
            criteria_parts.append(f"subject:{subject}")
        if query:
            criteria_parts.append(query)
        console.print(f"[dim]Matches: {' '.join(criteria_parts)}[/dim]")

    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)


@app.command("filter-delete")
def delete_filter(
    filter_id: str = typer.Argument(..., help="Filter ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a Gmail filter."""
    require_auth()

    if not yes and not confirm(f"Delete filter {filter_id}?"):
        console.print("Cancelled.")
        return

    client = GmailClient()
    try:
        client.delete_filter(filter_id)
        display_success("Filter deleted.")
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)
    except RuntimeError as e:
        display_error(str(e))
        raise typer.Exit(1)
