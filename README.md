# Assistant CLI

A command-line tool for interacting with Gmail and Google Calendar.

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

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Select **External** user type (or Internal if you have Google Workspace)
3. Fill in the required fields:
   - App name: "Assistant CLI"
   - User support email: your email
   - Developer contact email: your email
4. Click **Save and Continue**
5. On the Scopes page, click **Add or Remove Scopes**
6. Add these scopes:
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/gmail.compose`
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.settings.basic`
   - `https://www.googleapis.com/auth/calendar`
7. Click **Save and Continue**
8. On the Test users page, add your email address(es)
9. Click **Save and Continue**

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
