# Assistant CLI Reference

Command-line tool for Gmail and Google Calendar management.

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
assistant gmail trash <message_id>
assistant gmail delete <message_id>
assistant gmail mark-read <message_id>
assistant gmail mark-unread <message_id>
assistant gmail archive <message_id>
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
