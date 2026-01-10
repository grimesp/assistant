# Assistant CLI Reference

Command-line tool for Gmail, Google Calendar, Google Sheets, and Google Drive management.

## Accounts

Multi-account support. When the user specifies an account, switch to it before running commands.

Account aliases are stored in `~/.config/assistant/config.json`. Check there for shorthand names.

Example: "Check my work email" → run `assistant auth switch work` first (using alias from config).

To see available accounts: `assistant auth list`

## Authentication

```bash
assistant auth login              # Add a new account
assistant auth list               # List all accounts
assistant auth status             # Show accounts with active indicator
assistant auth switch <email>     # Switch active account (partial match OK)
assistant auth logout [email]     # Logout specific or active account
assistant auth logout --all       # Logout all accounts
```

## Gmail Commands

### Reading
```bash
assistant gmail list                      # Recent emails
assistant gmail list --limit 50           # More results
assistant gmail list --label INBOX        # Filter by label
assistant gmail search "from:user@example.com"
assistant gmail search "is:unread"
assistant gmail read <message_id>
```

### Composing
```bash
assistant gmail compose --to user@example.com --subject "Subject" --body "Body"
assistant gmail compose --to user@example.com --subject "Subject"  # Opens editor
assistant gmail compose --to user@example.com --subject "Report" --attach file.pdf
```

### Replying & Forwarding
```bash
assistant gmail reply <message_id>
assistant gmail reply <message_id> --all
assistant gmail forward <message_id> --to recipient@example.com
```

### Drafts
```bash
assistant gmail drafts                    # List drafts
assistant gmail draft --to user@example.com --subject "Draft"
assistant gmail send-draft <draft_id>
assistant gmail delete-draft <draft_id>
```

### Organization
```bash
assistant gmail labels
assistant gmail label-create <name>                 # Create a new label
assistant gmail label-apply <label> --query "..."   # Apply label to matching emails
assistant gmail trash <message_id>
assistant gmail delete <message_id>
assistant gmail mark-read <message_id>
assistant gmail mark-read --all-unread              # Mark all unread as read
assistant gmail mark-unread <message_id>
assistant gmail archive <message_id>
assistant gmail archive --all-inbox                 # Archive entire inbox
assistant gmail clear-inbox                         # Archive read, non-starred only
assistant gmail clear-inbox --yes                   # Skip confirmation
assistant gmail label <message_id> --add LABEL --remove LABEL
```

### Attachments
```bash
assistant gmail attachments <message_id>                       # List
assistant gmail attachments <message_id> --download ./path     # Download
```

### Filters
```bash
assistant gmail filters                                        # List all filters
assistant gmail filter-create --from example.com --archive     # Create filter
assistant gmail filter-create --from news@x.com --mark-read --archive
assistant gmail filter-create --subject "urgent" --star
assistant gmail filter-delete <filter_id>                      # Delete filter
assistant gmail filter-delete <filter_id> --yes                # Skip confirmation
```

Filter options: `--from`, `--to`, `--subject`, `--query`, `--archive`, `--mark-read`, `--star`, `--trash`, `--add-label`, `--remove-label`, `--forward`, `--category`

### Search Syntax
- `from:`, `to:`, `subject:` - Filter by field
- `is:unread`, `is:starred` - Status filters
- `has:attachment` - Attachment filter
- `after:2024/01/01`, `before:2024/12/31` - Date range
- `label:work` - Label filter
- `"exact phrase"` - Exact match

## Calendar Commands

### Viewing
```bash
assistant calendar list               # Next 7 days
assistant calendar list --days 30     # Custom range
assistant calendar today              # Today's events
assistant calendar week               # This week
assistant calendar show <event_id>    # Event details
assistant calendar calendars          # List calendars
```

### Creating
```bash
assistant calendar create --title "Meeting" --start "2024-01-15 14:00" --end "2024-01-15 15:00"
assistant calendar create --title "Holiday" --start "2024-01-15" --all-day
assistant calendar create --title "Sync" --start "tomorrow 2pm" --attendee user@example.com
assistant calendar create --title "Standup" --start "2024-01-13 09:00" --recurrence "FREQ=WEEKLY;BYDAY=MO,WE,FR"
assistant calendar quick "Meeting with John tomorrow at 3pm"
```

Recurrence examples (RRULE format):
- `FREQ=DAILY` - every day
- `FREQ=WEEKLY;BYDAY=TU,TH` - every Tuesday and Thursday
- `FREQ=MONTHLY;BYMONTHDAY=15` - 15th of each month

### Editing & Deleting
```bash
assistant calendar edit <event_id> --title "New Title"
assistant calendar edit <event_id> --start "2024-01-16 10:00"
assistant calendar edit <event_id> --location "Room A"
assistant calendar delete <event_id>
```

### Responding to Invitations
```bash
assistant calendar respond <event_id> --accept
assistant calendar respond <event_id> --decline
assistant calendar respond <event_id> --tentative
```

## Sheets Commands

### Viewing
```bash
assistant sheets list                              # List recent spreadsheets
assistant sheets list --limit 50                   # More results
assistant sheets show <spreadsheet_id>             # Show spreadsheet details and sheets
assistant sheets read <spreadsheet_id> "Sheet1!A1:C10"   # Read cell data
assistant sheets read <spreadsheet_id> "A1:C10" --formulas   # Show formulas
```

### Writing
```bash
assistant sheets write <spreadsheet_id> "Sheet1!A1" --value "Hello"
assistant sheets write <spreadsheet_id> "Sheet1!A1:C1" --value "A,B,C"
assistant sheets write <spreadsheet_id> "Sheet1!A1" --csv data.csv
assistant sheets append <spreadsheet_id> "Sheet1" --value "New,Row,Data"
assistant sheets append <spreadsheet_id> "Sheet1" --csv more_data.csv
assistant sheets clear <spreadsheet_id> "Sheet1!A1:C10"
assistant sheets clear <spreadsheet_id> "Sheet1!A1:C10" --yes   # Skip confirmation
```

### Creating & Managing
```bash
assistant sheets create --title "New Spreadsheet"
assistant sheets add-sheet <spreadsheet_id> --title "New Sheet"
assistant sheets delete-sheet <spreadsheet_id> <sheet_id>
assistant sheets delete-sheet <spreadsheet_id> <sheet_id> --yes
assistant sheets rename-sheet <spreadsheet_id> <sheet_id> --title "Renamed"
```

### Range Notation
- `Sheet1!A1:C10` - Cells A1 to C10 on Sheet1
- `A1:C10` - Cells on the first sheet
- `Sheet1` - Entire sheet (for append operations)
- `Sheet1!A:C` - Columns A through C

## Drive Commands

### Viewing
```bash
assistant drive list                           # List recent files
assistant drive list --limit 50                # More results
assistant drive list --query "report"          # Search by name
assistant drive info <file_id>                 # Show file metadata
assistant drive info "https://drive.google.com/file/d/..."  # Also accepts URLs
```

### Downloading
```bash
assistant drive download <file_id>             # Download to current directory
assistant drive download <file_id> -o ./path   # Download to specific path
assistant drive download <url>                 # Download from Google Drive URL
assistant drive download <file_id> -f csv      # Export Google Sheet as CSV
assistant drive download <file_id> -f pdf      # Export as PDF
assistant drive download <file_id> -f xlsx     # Export Google Sheet as Excel
assistant drive download <file_id> -f docx     # Export Google Doc as Word
```

### URL Support
These Google Drive URL formats are supported:
- `https://drive.google.com/file/d/{FILE_ID}/view`
- `https://drive.google.com/open?id={FILE_ID}`
- `https://docs.google.com/document/d/{FILE_ID}/...`
- `https://docs.google.com/spreadsheets/d/{FILE_ID}/...`
- `https://docs.google.com/presentation/d/{FILE_ID}/...`

### Export Formats
For Google Workspace files, available export formats:
- **Google Docs**: pdf (default), docx, txt, html
- **Google Sheets**: csv (default), xlsx, pdf
- **Google Slides**: pdf (default), pptx
- **Google Drawings**: png (default), pdf, svg
