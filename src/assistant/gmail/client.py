"""Gmail API client wrapper."""

import base64
import os
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mimetypes import guess_type
from pathlib import Path
from typing import Any, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..auth import get_credentials


class GmailClient:
    """Wrapper class for Gmail API operations."""

    def __init__(self):
        """Initialize the Gmail client."""
        self._service = None

    @property
    def service(self):
        """Get or create the Gmail API service."""
        if self._service is None:
            creds = get_credentials()
            if creds is None:
                raise RuntimeError("Not authenticated. Run 'assistant auth login' first.")
            self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def list_messages(
        self,
        query: str = "",
        max_results: int = 20,
        label_ids: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        List messages matching the given query.

        Args:
            query: Gmail search query string
            max_results: Maximum number of messages to return
            label_ids: List of label IDs to filter by

        Returns:
            List of message dictionaries with id, from, subject, date, snippet, unread
        """
        try:
            params = {
                "userId": "me",
                "maxResults": max_results,
            }
            if query:
                params["q"] = query
            if label_ids:
                params["labelIds"] = label_ids

            response = self.service.users().messages().list(**params).execute()
            messages = response.get("messages", [])

            result = []
            for msg in messages:
                msg_detail = self.get_message(msg["id"], minimal=True)
                if msg_detail:
                    result.append(msg_detail)

            return result
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def get_message(self, message_id: str, minimal: bool = False) -> Optional[dict]:
        """
        Get a single message by ID.

        Args:
            message_id: The message ID
            minimal: If True, return minimal info for list views

        Returns:
            Message dictionary with full details
        """
        try:
            format_type = "metadata" if minimal else "full"
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format=format_type)
                .execute()
            )

            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

            result = {
                "id": msg["id"],
                "thread_id": msg.get("threadId"),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "cc": headers.get("cc", ""),
                "subject": headers.get("subject", "(No Subject)"),
                "date": headers.get("date", ""),
                "snippet": msg.get("snippet", ""),
                "unread": "UNREAD" in msg.get("labelIds", []),
                "labels": msg.get("labelIds", []),
            }

            if not minimal:
                # Extract body
                result["body"] = self._extract_body(msg.get("payload", {}))
                # Extract attachments info
                result["attachments"] = self._extract_attachments_info(msg.get("payload", {}))

            return result
        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise RuntimeError(f"Gmail API error: {e}")

    def _extract_body(self, payload: dict) -> str:
        """Extract the message body from payload."""
        body = ""

        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        elif "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/plain":
                    if part.get("body", {}).get("data"):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        break
                elif mime_type == "text/html" and not body:
                    if part.get("body", {}).get("data"):
                        # Fall back to HTML if no plain text
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                elif mime_type.startswith("multipart/"):
                    # Recursively extract from nested parts
                    body = self._extract_body(part)
                    if body:
                        break

        return body

    def _extract_attachments_info(self, payload: dict) -> list[dict]:
        """Extract attachment information from payload."""
        attachments = []

        def extract_from_parts(parts):
            for part in parts:
                filename = part.get("filename")
                if filename:
                    attachments.append({
                        "id": part.get("body", {}).get("attachmentId"),
                        "filename": filename,
                        "mimeType": part.get("mimeType", ""),
                        "size": part.get("body", {}).get("size", 0),
                    })
                if "parts" in part:
                    extract_from_parts(part["parts"])

        if "parts" in payload:
            extract_from_parts(payload["parts"])
        elif payload.get("filename"):
            # Handle single-part messages where the payload itself is the attachment
            attachments.append({
                "id": payload.get("body", {}).get("attachmentId"),
                "filename": payload["filename"],
                "mimeType": payload.get("mimeType", ""),
                "size": payload.get("body", {}).get("size", 0),
            })

        return attachments

    def search(self, query: str, max_results: int = 20) -> list[dict]:
        """
        Search for messages matching the query.

        Args:
            query: Gmail search query string
            max_results: Maximum number of results

        Returns:
            List of message dictionaries
        """
        return self.list_messages(query=query, max_results=max_results)

    def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        attachments: Optional[list[str]] = None,
        reply_to_message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        is_html: bool = False,
    ) -> dict:
        """
        Send an email message.

        Args:
            to: Recipient email address(es)
            subject: Email subject
            body: Email body text
            cc: CC recipients
            bcc: BCC recipients
            attachments: List of file paths to attach
            reply_to_message_id: Message ID if this is a reply
            thread_id: Thread ID to add this message to
            is_html: If True, send body as HTML instead of plain text

        Returns:
            Sent message info
        """
        try:
            # Get sender info
            profile = self.service.users().getProfile(userId="me").execute()
            sender = profile.get("emailAddress", "")

            subtype = "html" if is_html else "plain"
            if attachments:
                message = MIMEMultipart()
                message.attach(MIMEText(body, subtype))

                for file_path in attachments:
                    path = Path(file_path)
                    if not path.exists():
                        raise FileNotFoundError(f"Attachment not found: {file_path}")

                    content_type, _ = guess_type(str(path))
                    if content_type is None:
                        content_type = "application/octet-stream"

                    main_type, sub_type = content_type.split("/", 1)

                    with open(path, "rb") as f:
                        attachment = MIMEBase(main_type, sub_type)
                        attachment.set_payload(f.read())

                    from email.encoders import encode_base64
                    encode_base64(attachment)
                    attachment.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=path.name,
                    )
                    message.attach(attachment)
            else:
                message = MIMEText(body, subtype)

            message["to"] = to
            message["from"] = sender
            message["subject"] = subject

            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc

            # Handle reply headers
            if reply_to_message_id:
                original = self.get_message(reply_to_message_id)
                if original:
                    message["In-Reply-To"] = reply_to_message_id
                    message["References"] = reply_to_message_id

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            body_data = {"raw": raw}
            if thread_id:
                body_data["threadId"] = thread_id

            sent = (
                self.service.users()
                .messages()
                .send(userId="me", body=body_data)
                .execute()
            )

            return {"id": sent["id"], "thread_id": sent.get("threadId")}
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        attachments: Optional[list[str]] = None,
    ) -> dict:
        """
        Create a draft email.

        Args:
            to: Recipient email address(es)
            subject: Email subject
            body: Email body text
            cc: CC recipients
            attachments: List of file paths to attach

        Returns:
            Draft info with ID
        """
        try:
            profile = self.service.users().getProfile(userId="me").execute()
            sender = profile.get("emailAddress", "")

            if attachments:
                message = MIMEMultipart()
                message.attach(MIMEText(body, "plain"))

                for file_path in attachments:
                    path = Path(file_path)
                    if not path.exists():
                        raise FileNotFoundError(f"Attachment not found: {file_path}")

                    content_type, _ = guess_type(str(path))
                    if content_type is None:
                        content_type = "application/octet-stream"

                    main_type, sub_type = content_type.split("/", 1)

                    with open(path, "rb") as f:
                        attachment = MIMEBase(main_type, sub_type)
                        attachment.set_payload(f.read())

                    from email.encoders import encode_base64
                    encode_base64(attachment)
                    attachment.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=path.name,
                    )
                    message.attach(attachment)
            else:
                message = MIMEText(body, "plain")

            message["to"] = to
            message["from"] = sender
            message["subject"] = subject
            if cc:
                message["cc"] = cc

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            draft = (
                self.service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw}})
                .execute()
            )

            return {"id": draft["id"]}
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def reply(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
    ) -> dict:
        """
        Reply to a message.

        Args:
            message_id: The message ID to reply to
            body: Reply body text
            reply_all: If True, reply to all recipients

        Returns:
            Sent message info
        """
        original = self.get_message(message_id)
        if not original:
            raise ValueError(f"Message not found: {message_id}")

        # Determine recipients
        to = original["from"]
        cc = ""
        if reply_all:
            # Get original recipients excluding ourselves
            profile = self.service.users().getProfile(userId="me").execute()
            my_email = profile.get("emailAddress", "")

            orig_to = original.get("to", "")
            orig_cc = original.get("cc", "")

            # Combine all recipients except ourselves
            all_recipients = []
            for addr in (orig_to + "," + orig_cc).split(","):
                addr = addr.strip()
                if addr and my_email.lower() not in addr.lower():
                    all_recipients.append(addr)

            if all_recipients:
                cc = ", ".join(all_recipients)

        # Prepare subject with Re: prefix
        subject = original["subject"]
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        return self.send_message(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            reply_to_message_id=message_id,
            thread_id=original.get("thread_id"),
        )

    def forward(self, message_id: str, to: str, body: str = "") -> dict:
        """
        Forward a message.

        Args:
            message_id: The message ID to forward
            to: Recipient to forward to
            body: Optional additional body text

        Returns:
            Sent message info
        """
        original = self.get_message(message_id)
        if not original:
            raise ValueError(f"Message not found: {message_id}")

        # Prepare subject with Fwd: prefix
        subject = original["subject"]
        if not subject.lower().startswith("fwd:"):
            subject = f"Fwd: {subject}"

        # Build forwarded message body
        forward_body = body + "\n\n" if body else ""
        forward_body += "---------- Forwarded message ----------\n"
        forward_body += f"From: {original['from']}\n"
        forward_body += f"Date: {original['date']}\n"
        forward_body += f"Subject: {original['subject']}\n"
        forward_body += f"To: {original['to']}\n"
        forward_body += "\n"
        forward_body += original.get("body", "")

        return self.send_message(to=to, subject=subject, body=forward_body)

    def trash_message(self, message_id: str) -> bool:
        """
        Move a message to trash.

        Args:
            message_id: The message ID

        Returns:
            True if successful
        """
        try:
            self.service.users().messages().trash(userId="me", id=message_id).execute()
            return True
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def untrash_message(self, message_id: str) -> bool:
        """
        Remove a message from trash.

        Args:
            message_id: The message ID

        Returns:
            True if successful
        """
        try:
            self.service.users().messages().untrash(userId="me", id=message_id).execute()
            return True
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def delete_message(self, message_id: str) -> bool:
        """
        Permanently delete a message.

        Args:
            message_id: The message ID

        Returns:
            True if successful
        """
        try:
            self.service.users().messages().delete(userId="me", id=message_id).execute()
            return True
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def modify_labels(
        self,
        message_id: str,
        add_labels: Optional[list[str]] = None,
        remove_labels: Optional[list[str]] = None,
    ) -> bool:
        """
        Modify labels on a message.

        Args:
            message_id: The message ID
            add_labels: Labels to add
            remove_labels: Labels to remove

        Returns:
            True if successful
        """
        try:
            body = {}
            if add_labels:
                body["addLabelIds"] = add_labels
            if remove_labels:
                body["removeLabelIds"] = remove_labels

            self.service.users().messages().modify(
                userId="me", id=message_id, body=body
            ).execute()
            return True
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read."""
        return self.modify_labels(message_id, remove_labels=["UNREAD"])

    def mark_as_unread(self, message_id: str) -> bool:
        """Mark a message as unread."""
        return self.modify_labels(message_id, add_labels=["UNREAD"])

    def archive(self, message_id: str) -> bool:
        """Archive a message (remove from inbox)."""
        return self.modify_labels(message_id, remove_labels=["INBOX"])

    def get_attachment(
        self,
        message_id: str,
        attachment_id: str,
        filename: str,
        download_dir: str = ".",
    ) -> str:
        """
        Download an attachment.

        Args:
            message_id: The message ID
            attachment_id: The attachment ID
            filename: The filename to save as
            download_dir: Directory to save the file

        Returns:
            Path to the downloaded file
        """
        try:
            attachment = (
                self.service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )

            data = base64.urlsafe_b64decode(attachment["data"])

            download_path = Path(download_dir)
            download_path.mkdir(parents=True, exist_ok=True)

            file_path = download_path / filename

            # Handle filename conflicts
            counter = 1
            original_stem = file_path.stem
            while file_path.exists():
                file_path = download_path / f"{original_stem}_{counter}{file_path.suffix}"
                counter += 1

            with open(file_path, "wb") as f:
                f.write(data)

            return str(file_path)
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def list_labels(self) -> list[dict]:
        """
        List all labels.

        Returns:
            List of label dictionaries
        """
        try:
            response = self.service.users().labels().list(userId="me").execute()
            labels = response.get("labels", [])

            result = []
            for label in labels:
                # Get full label details
                label_detail = (
                    self.service.users()
                    .labels()
                    .get(userId="me", id=label["id"])
                    .execute()
                )
                result.append({
                    "id": label_detail["id"],
                    "name": label_detail["name"],
                    "type": label_detail.get("type", "user"),
                    "messagesTotal": label_detail.get("messagesTotal", 0),
                    "messagesUnread": label_detail.get("messagesUnread", 0),
                })

            return sorted(result, key=lambda x: x["name"])
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def get_label_id(self, name: str) -> Optional[str]:
        """
        Get a label ID by name.

        Args:
            name: The label name

        Returns:
            Label ID if found, None otherwise
        """
        try:
            response = self.service.users().labels().list(userId="me").execute()
            labels = response.get("labels", [])
            for label in labels:
                if label["name"].lower() == name.lower():
                    return label["id"]
            return None
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def create_label(self, name: str) -> dict:
        """
        Create a new label.

        Args:
            name: The label name

        Returns:
            Created label dictionary with id and name
        """
        try:
            label_body = {
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            label = (
                self.service.users()
                .labels()
                .create(userId="me", body=label_body)
                .execute()
            )
            return {
                "id": label["id"],
                "name": label["name"],
            }
        except HttpError as e:
            if e.resp.status == 409:
                raise ValueError(f"Label already exists: {name}")
            raise RuntimeError(f"Gmail API error: {e}")

    def list_drafts(self) -> list[dict]:
        """
        List all drafts.

        Returns:
            List of draft dictionaries
        """
        try:
            response = self.service.users().drafts().list(userId="me").execute()
            drafts = response.get("drafts", [])

            result = []
            for draft in drafts:
                draft_detail = (
                    self.service.users()
                    .drafts()
                    .get(userId="me", id=draft["id"])
                    .execute()
                )
                msg = draft_detail.get("message", {})
                headers = {
                    h["name"].lower(): h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }
                result.append({
                    "id": draft["id"],
                    "message_id": msg.get("id"),
                    "to": headers.get("to", ""),
                    "subject": headers.get("subject", "(No Subject)"),
                })

            return result
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def send_draft(self, draft_id: str) -> dict:
        """
        Send a draft.

        Args:
            draft_id: The draft ID

        Returns:
            Sent message info
        """
        try:
            sent = (
                self.service.users()
                .drafts()
                .send(userId="me", body={"id": draft_id})
                .execute()
            )
            return {"id": sent["id"], "thread_id": sent.get("threadId")}
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def delete_draft(self, draft_id: str) -> bool:
        """
        Delete a draft.

        Args:
            draft_id: The draft ID

        Returns:
            True if successful
        """
        try:
            self.service.users().drafts().delete(userId="me", id=draft_id).execute()
            return True
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def get_profile(self) -> dict:
        """
        Get the user's Gmail profile.

        Returns:
            Profile dictionary with email address and other info
        """
        try:
            profile = self.service.users().getProfile(userId="me").execute()
            return {
                "email": profile.get("emailAddress", ""),
                "messages_total": profile.get("messagesTotal", 0),
                "threads_total": profile.get("threadsTotal", 0),
                "history_id": profile.get("historyId", ""),
            }
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def list_filters(self) -> list[dict]:
        """
        List all Gmail filters.

        Returns:
            List of filter dictionaries
        """
        try:
            response = self.service.users().settings().filters().list(userId="me").execute()
            filters = response.get("filter", [])

            result = []
            for f in filters:
                criteria = f.get("criteria", {})
                action = f.get("action", {})
                result.append({
                    "id": f["id"],
                    "from": criteria.get("from", ""),
                    "to": criteria.get("to", ""),
                    "subject": criteria.get("subject", ""),
                    "query": criteria.get("query", ""),
                    "add_labels": action.get("addLabelIds", []),
                    "remove_labels": action.get("removeLabelIds", []),
                    "forward": action.get("forward", ""),
                })

            return result
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def create_filter(
        self,
        from_addr: Optional[str] = None,
        to_addr: Optional[str] = None,
        subject: Optional[str] = None,
        query: Optional[str] = None,
        add_labels: Optional[list[str]] = None,
        remove_labels: Optional[list[str]] = None,
        forward_to: Optional[str] = None,
        mark_read: bool = False,
        star: bool = False,
        archive: bool = False,
        trash: bool = False,
        never_spam: bool = False,
        important: Optional[bool] = None,
        category: Optional[str] = None,
    ) -> dict:
        """
        Create a Gmail filter.

        Args:
            from_addr: Filter by sender
            to_addr: Filter by recipient
            subject: Filter by subject
            query: Gmail search query
            add_labels: Labels to add
            remove_labels: Labels to remove
            forward_to: Email to forward to
            mark_read: Mark matching messages as read
            star: Star matching messages
            archive: Archive matching messages (skip inbox)
            trash: Move to trash
            never_spam: Never mark as spam
            important: Mark as important (True) or not important (False)
            category: Category to apply (e.g., 'primary', 'social', 'promotions')

        Returns:
            Created filter info
        """
        try:
            # Build criteria
            criteria = {}
            if from_addr:
                criteria["from"] = from_addr
            if to_addr:
                criteria["to"] = to_addr
            if subject:
                criteria["subject"] = subject
            if query:
                criteria["query"] = query

            if not criteria:
                raise ValueError("At least one filter criteria is required")

            # Build action
            action = {}

            # System labels can be used directly, user labels need ID lookup
            system_labels = {
                "INBOX", "SPAM", "TRASH", "UNREAD", "STARRED", "IMPORTANT",
                "SENT", "DRAFT", "CATEGORY_PERSONAL", "CATEGORY_SOCIAL",
                "CATEGORY_PROMOTIONS", "CATEGORY_UPDATES", "CATEGORY_FORUMS",
            }

            add_label_ids = []
            if add_labels:
                for label in add_labels:
                    if label.upper() in system_labels:
                        add_label_ids.append(label.upper())
                    else:
                        label_id = self.get_label_id(label)
                        if not label_id:
                            raise ValueError(f"Label not found: {label}")
                        add_label_ids.append(label_id)

            remove_label_ids = []
            if remove_labels:
                for label in remove_labels:
                    if label.upper() in system_labels:
                        remove_label_ids.append(label.upper())
                    else:
                        label_id = self.get_label_id(label)
                        if not label_id:
                            raise ValueError(f"Label not found: {label}")
                        remove_label_ids.append(label_id)

            if archive:
                remove_label_ids.append("INBOX")
            if trash:
                add_label_ids.append("TRASH")
            if mark_read:
                remove_label_ids.append("UNREAD")
            if star:
                add_label_ids.append("STARRED")
            if never_spam:
                remove_label_ids.append("SPAM")
            if important is True:
                add_label_ids.append("IMPORTANT")
            elif important is False:
                remove_label_ids.append("IMPORTANT")
            if category:
                category_map = {
                    "primary": "CATEGORY_PERSONAL",
                    "social": "CATEGORY_SOCIAL",
                    "promotions": "CATEGORY_PROMOTIONS",
                    "updates": "CATEGORY_UPDATES",
                    "forums": "CATEGORY_FORUMS",
                }
                if category.lower() in category_map:
                    add_label_ids.append(category_map[category.lower()])

            if add_label_ids:
                action["addLabelIds"] = list(set(add_label_ids))
            if remove_label_ids:
                action["removeLabelIds"] = list(set(remove_label_ids))
            if forward_to:
                action["forward"] = forward_to

            if not action:
                raise ValueError("At least one filter action is required")

            filter_body = {
                "criteria": criteria,
                "action": action,
            }

            created = (
                self.service.users()
                .settings()
                .filters()
                .create(userId="me", body=filter_body)
                .execute()
            )

            return {"id": created["id"], "criteria": criteria, "action": action}
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")

    def delete_filter(self, filter_id: str) -> bool:
        """
        Delete a Gmail filter.

        Args:
            filter_id: The filter ID

        Returns:
            True if successful
        """
        try:
            self.service.users().settings().filters().delete(
                userId="me", id=filter_id
            ).execute()
            return True
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Filter not found: {filter_id}")
            raise RuntimeError(f"Gmail API error: {e}")
