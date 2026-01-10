# Assistant CLI

A command-line tool for interacting with Gmail, Google Calendar, Google Sheets, and Google Drive.

## Installation

1. Install the package in development mode:

```bash
pip install -e .
```

## Google Cloud Setup

Before using the CLI, you need to set up Google Cloud credentials:

### Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** at the top of the page
3. Click **New Project**
4. Enter a project name (e.g., "Assistant CLI") and click **Create**

### Step 2: Enable APIs

1. In your project, go to **APIs & Services > Library**
2. Search for and enable these APIs:
   - **Gmail API**
   - **Google Calendar API**
   - **Google Sheets API**
   - **Google Drive API**

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Select **External** user type (or Internal if you have Google Workspace)
3. Fill in the required fields:
   - App name: "Assistant CLI"
   - User support email: your email
   - Developer contact email: your email
4. Click **Save and Continue** through the remaining steps (Scopes, Test users)
   - You can skip adding scopes - the app requests them at runtime
   - For External apps in testing mode, add your email as a test user

### Step 4: Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Select **Desktop app** as the application type
4. Enter a name (e.g., "Assistant CLI Desktop")
5. Click **Create**
6. Click **Download JSON** to download your credentials
7. Rename the downloaded file to `credentials.json`
8. Move it to `~/.config/assistant/credentials.json`

```bash
mkdir -p ~/.config/assistant
mv ~/Downloads/client_secret_*.json ~/.config/assistant/credentials.json
```

## Usage

### Authentication

Authenticate with your Google account:

```bash
assistant auth login
```

This will open a browser window for you to authorize the application.

#### Multi-Account Support

You can authenticate multiple accounts:

```bash
assistant auth login          # Add another account
assistant auth list           # List all accounts
assistant auth switch <email> # Switch active account
assistant auth status         # Show current status
assistant auth logout         # Logout active account
assistant auth logout --all   # Logout all accounts
```

### Gmail Commands

List recent emails:
```bash
assistant gmail list
assistant gmail list --limit 50
assistant gmail list --label INBOX
```

Search emails:
```bash
assistant gmail search "from:someone@example.com"
assistant gmail search "subject:important"
assistant gmail search "is:unread"
```

Read an email:
```bash
assistant gmail read <message_id>
```

Compose and send:
```bash
# With body on command line
assistant gmail compose --to user@example.com --subject "Hello" --body "Message body"

# Opens editor for body
assistant gmail compose --to user@example.com --subject "Hello"

# With attachments
assistant gmail compose --to user@example.com --subject "Report" --attach report.pdf
```

Reply to an email:
```bash
assistant gmail reply <message_id>
assistant gmail reply <message_id> --all  # Reply to all
```

Forward an email:
```bash
assistant gmail forward <message_id> --to recipient@example.com
```

Manage drafts:
```bash
assistant gmail drafts              # List drafts
assistant gmail draft --to user@example.com --subject "Draft"
assistant gmail send-draft <draft_id>
assistant gmail delete-draft <draft_id>
```

List labels:
```bash
assistant gmail labels
```

Manage messages:
```bash
assistant gmail trash <message_id>
assistant gmail delete <message_id>
assistant gmail mark-read <message_id>
assistant gmail mark-unread <message_id>
assistant gmail archive <message_id>
assistant gmail label <message_id> --add LABEL --remove LABEL
```

Download attachments:
```bash
assistant gmail attachments <message_id>                    # List attachments
assistant gmail attachments <message_id> --download ./downloads  # Download all
```

Manage filters:
```bash
assistant gmail filters                                     # List filters
assistant gmail filter-create --from example.com --archive  # Create filter
assistant gmail filter-delete <filter_id>                   # Delete filter
```

### Calendar Commands

View events:
```bash
assistant calendar list              # Next 7 days
assistant calendar list --days 30    # Next 30 days
assistant calendar today             # Today's events
assistant calendar week              # This week's events
assistant calendar show <event_id>   # Event details
```

List calendars:
```bash
assistant calendar calendars
```

Create events:
```bash
# With specific times
assistant calendar create --title "Meeting" --start "2024-01-15 14:00" --end "2024-01-15 15:00"

# All-day event
assistant calendar create --title "Holiday" --start "2024-01-15" --all-day

# With attendees
assistant calendar create --title "Team Sync" --start "tomorrow 2pm" --attendee user1@example.com

# With recurrence
assistant calendar create --title "Standup" --start "2024-01-13 09:00" --recurrence "FREQ=WEEKLY;BYDAY=MO,WE,FR"

# Quick add (natural language)
assistant calendar quick "Meeting with John tomorrow at 3pm"
```

Edit events:
```bash
assistant calendar edit <event_id> --title "New Title"
assistant calendar edit <event_id> --start "2024-01-16 10:00"
assistant calendar edit <event_id> --location "Conference Room A"
```

Delete events:
```bash
assistant calendar delete <event_id>
assistant calendar delete <event_id> --yes  # Skip confirmation
```

Respond to invitations:
```bash
assistant calendar respond <event_id> --accept
assistant calendar respond <event_id> --decline
assistant calendar respond <event_id> --tentative
```

### Sheets Commands

List spreadsheets:
```bash
assistant sheets list
assistant sheets list --limit 50
```

View spreadsheet details:
```bash
assistant sheets show <spreadsheet_id>
```

Read data:
```bash
assistant sheets read <spreadsheet_id> "Sheet1!A1:C10"
assistant sheets read <spreadsheet_id> "A1:C10" --formulas  # Show formulas
```

Write data:
```bash
assistant sheets write <spreadsheet_id> "Sheet1!A1" --value "Hello"
assistant sheets write <spreadsheet_id> "Sheet1!A1:C1" --value "A,B,C"
assistant sheets write <spreadsheet_id> "Sheet1!A1" --csv data.csv
```

Append rows:
```bash
assistant sheets append <spreadsheet_id> "Sheet1" --value "New,Row,Data"
assistant sheets append <spreadsheet_id> "Sheet1" --csv more_data.csv
```

Create and manage:
```bash
assistant sheets create --title "New Spreadsheet"
assistant sheets add-sheet <spreadsheet_id> --title "New Sheet"
assistant sheets delete-sheet <spreadsheet_id> <sheet_id>
assistant sheets rename-sheet <spreadsheet_id> <sheet_id> --title "Renamed"
assistant sheets clear <spreadsheet_id> "Sheet1!A1:C10"
```

### Drive Commands

List files:
```bash
assistant drive list
assistant drive list --limit 50
assistant drive list --query "report"  # Search by name
```

View file info:
```bash
assistant drive info <file_id>
assistant drive info "https://drive.google.com/file/d/..."  # Also accepts URLs
```

Download files:
```bash
assistant drive download <file_id>
assistant drive download <file_id> -o ./path      # Specific output path
assistant drive download <url>                     # Download from URL
assistant drive download <file_id> -f csv          # Export Google Sheets as CSV
assistant drive download <file_id> -f pdf          # Export as PDF
assistant drive download <file_id> -f xlsx         # Export as Excel
assistant drive download <file_id> -f docx         # Export Google Docs as Word
```

Supported Google Drive URL formats:
- `https://drive.google.com/file/d/{FILE_ID}/view`
- `https://drive.google.com/open?id={FILE_ID}`
- `https://docs.google.com/document/d/{FILE_ID}/...`
- `https://docs.google.com/spreadsheets/d/{FILE_ID}/...`

Export formats for Google Workspace files:
- **Google Docs**: pdf (default), docx, txt, html
- **Google Sheets**: csv (default), xlsx, pdf
- **Google Slides**: pdf (default), pptx
- **Google Drawings**: png (default), pdf, svg

## Gmail Search Syntax

The search command supports Gmail's full search syntax:

- `from:sender@example.com` - From a specific sender
- `to:recipient@example.com` - To a specific recipient
- `subject:keyword` - Subject contains keyword
- `is:unread` - Unread messages
- `is:starred` - Starred messages
- `has:attachment` - Messages with attachments
- `after:2024/01/01` - After a date
- `before:2024/12/31` - Before a date
- `label:work` - Messages with a label
- `"exact phrase"` - Exact phrase match

Combine multiple operators: `from:boss@company.com is:unread after:2024/01/01`

## Environment Variables

- `EDITOR` or `VISUAL` - Text editor for composing emails (defaults to vim)
- `ASSISTANT_CONFIG_DIR` - Override config directory (default: `~/.config/assistant`)

## Files

All configuration is stored in `~/.config/assistant/`:

```
~/.config/assistant/
├── credentials.json   # Google OAuth client credentials
├── config.json        # Account aliases and active account
└── tokens/            # Per-account authentication tokens
```

These files contain sensitive credentials and should not be shared.
