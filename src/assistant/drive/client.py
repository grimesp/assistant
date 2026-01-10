"""Google Drive API client wrapper."""

import io
import re
from pathlib import Path
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from ..auth import get_credentials


# Google Workspace MIME types and their export formats
EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": {
        "default": "application/pdf",
        "extension": ".pdf",
        "formats": {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
            "html": "text/html",
        },
    },
    "application/vnd.google-apps.spreadsheet": {
        "default": "text/csv",
        "extension": ".csv",
        "formats": {
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pdf": "application/pdf",
        },
    },
    "application/vnd.google-apps.presentation": {
        "default": "application/pdf",
        "extension": ".pdf",
        "formats": {
            "pdf": "application/pdf",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        },
    },
    "application/vnd.google-apps.drawing": {
        "default": "image/png",
        "extension": ".png",
        "formats": {
            "png": "image/png",
            "pdf": "application/pdf",
            "svg": "image/svg+xml",
        },
    },
}


class DriveClient:
    """Wrapper class for Google Drive API operations."""

    def __init__(self):
        """Initialize the Drive client."""
        self._service = None

    @property
    def service(self):
        """Get or create the Drive API service."""
        if self._service is None:
            creds = get_credentials()
            if creds is None:
                raise RuntimeError("Not authenticated. Run 'assistant auth login' first.")
            self._service = build("drive", "v3", credentials=creds)
        return self._service

    @staticmethod
    def extract_file_id(file_id_or_url: str) -> str:
        """
        Extract file ID from a Google Drive URL or return as-is if already an ID.

        Supported URL formats:
        - https://drive.google.com/file/d/{FILE_ID}/view
        - https://drive.google.com/open?id={FILE_ID}
        - https://docs.google.com/document/d/{FILE_ID}/...
        - https://docs.google.com/spreadsheets/d/{FILE_ID}/...
        - https://docs.google.com/presentation/d/{FILE_ID}/...

        Args:
            file_id_or_url: Either a file ID or a Google Drive URL

        Returns:
            The extracted file ID
        """
        # If it doesn't look like a URL, assume it's already an ID
        if not file_id_or_url.startswith("http"):
            return file_id_or_url

        # Pattern for /d/{id}/ format
        match = re.search(r"/d/([a-zA-Z0-9_-]+)", file_id_or_url)
        if match:
            return match.group(1)

        # Pattern for ?id={id} format
        match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", file_id_or_url)
        if match:
            return match.group(1)

        # If no pattern matches, return as-is (let the API handle the error)
        return file_id_or_url

    def get_file_metadata(self, file_id: str) -> dict:
        """
        Get metadata for a file.

        Args:
            file_id: The file ID or URL

        Returns:
            Dictionary with file metadata
        """
        file_id = self.extract_file_id(file_id)

        try:
            file_metadata = (
                self.service.files()
                .get(
                    fileId=file_id,
                    fields="id, name, mimeType, size, createdTime, modifiedTime, owners, webViewLink, parents, driveId",
                    supportsAllDrives=True,
                )
                .execute()
            )

            owners = file_metadata.get("owners", [])
            owner_email = owners[0].get("emailAddress", "") if owners else ""

            return {
                "id": file_metadata.get("id", ""),
                "name": file_metadata.get("name", ""),
                "mime_type": file_metadata.get("mimeType", ""),
                "size": int(file_metadata.get("size", 0)) if file_metadata.get("size") else None,
                "created_time": file_metadata.get("createdTime", ""),
                "modified_time": file_metadata.get("modifiedTime", ""),
                "owner": owner_email,
                "web_view_link": file_metadata.get("webViewLink", ""),
                "is_google_workspace": file_metadata.get("mimeType", "").startswith(
                    "application/vnd.google-apps."
                ),
            }
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"File not found: {file_id}")
            raise RuntimeError(f"Drive API error: {e}")

    def list_files(
        self,
        query: Optional[str] = None,
        max_results: int = 20,
        mime_type: Optional[str] = None,
    ) -> list[dict]:
        """
        List files the user has access to.

        Args:
            query: Optional search query (Drive query syntax)
            max_results: Maximum number of files to return
            mime_type: Optional MIME type filter

        Returns:
            List of file dictionaries
        """
        try:
            q_parts = []
            if query:
                q_parts.append(f"name contains '{query}'")
            if mime_type:
                q_parts.append(f"mimeType = '{mime_type}'")

            # Exclude trashed files
            q_parts.append("trashed = false")

            q = " and ".join(q_parts) if q_parts else None

            response = (
                self.service.files()
                .list(
                    q=q,
                    pageSize=max_results,
                    fields="files(id, name, mimeType, size, modifiedTime, owners, webViewLink, driveId)",
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
                    "mime_type": f.get("mimeType", ""),
                    "size": int(f.get("size", 0)) if f.get("size") else None,
                    "modified_time": f.get("modifiedTime", ""),
                    "owner": owner_email,
                    "web_view_link": f.get("webViewLink", ""),
                })

            return result
        except HttpError as e:
            raise RuntimeError(f"Drive API error: {e}")

    def download_file(
        self,
        file_id: str,
        output_path: Optional[str] = None,
        export_format: Optional[str] = None,
    ) -> str:
        """
        Download a file from Google Drive.

        For Google Workspace files (Docs, Sheets, Slides), exports to the specified
        or default format. For regular files, downloads directly.

        Args:
            file_id: The file ID or URL
            output_path: Optional output path. If not specified, uses current directory
                        with original filename.
            export_format: For Google Workspace files, the export format (e.g., 'pdf', 'csv')

        Returns:
            The path to the downloaded file
        """
        file_id = self.extract_file_id(file_id)

        # Get file metadata first
        metadata = self.get_file_metadata(file_id)
        mime_type = metadata["mime_type"]
        original_name = metadata["name"]

        # Determine if this is a Google Workspace file that needs export
        if mime_type in EXPORT_MIME_TYPES:
            return self._export_google_file(
                file_id, original_name, mime_type, output_path, export_format
            )
        else:
            return self._download_binary_file(file_id, original_name, output_path)

    def _export_google_file(
        self,
        file_id: str,
        original_name: str,
        mime_type: str,
        output_path: Optional[str],
        export_format: Optional[str],
    ) -> str:
        """Export a Google Workspace file to a downloadable format."""
        export_info = EXPORT_MIME_TYPES[mime_type]

        if export_format and export_format in export_info["formats"]:
            export_mime = export_info["formats"][export_format]
            extension = f".{export_format}"
        else:
            export_mime = export_info["default"]
            extension = export_info["extension"]

        # Determine output path
        if output_path:
            output = Path(output_path)
            if output.is_dir():
                output = output / f"{original_name}{extension}"
        else:
            output = Path.cwd() / f"{original_name}{extension}"

        try:
            request = self.service.files().export_media(
                fileId=file_id, mimeType=export_mime
            )

            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                _, done = downloader.next_chunk()

            output.write_bytes(fh.getvalue())
            return str(output)

        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"File not found: {file_id}")
            raise RuntimeError(f"Drive API error: {e}")

    def _download_binary_file(
        self,
        file_id: str,
        original_name: str,
        output_path: Optional[str],
    ) -> str:
        """Download a binary (non-Google Workspace) file."""
        # Determine output path
        if output_path:
            output = Path(output_path)
            if output.is_dir():
                output = output / original_name
        else:
            output = Path.cwd() / original_name

        try:
            request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)

            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                _, done = downloader.next_chunk()

            output.write_bytes(fh.getvalue())
            return str(output)

        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"File not found: {file_id}")
            raise RuntimeError(f"Drive API error: {e}")
