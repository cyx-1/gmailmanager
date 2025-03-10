# Gmail Manager

A Python tool for efficiently managing promotional emails in Gmail. This tool helps you clean up your inbox by analyzing promotional emails and providing options to either ignore specific senders or bulk delete their emails.

## Features

- Analyzes up to 1000 promotional emails to identify frequent senders
- Processes senders in order of frequency (most emails first)
- Shows unsubscribe links when available
- Maintains an ignore list for senders you want to keep
- Bulk deletes all emails from unwanted senders
- Preserves emails from ignored senders

## Prerequisites

1. Python 3.7 or higher
2. A Google Cloud Project with Gmail API enabled
3. OAuth 2.0 credentials (`credentials.json`) from Google Cloud Console

## Setup

1. Create a project in Google Cloud Console and enable Gmail API
2. Download OAuth credentials (`credentials.json`) and place in project root
3. Install dependencies using uv:
```bash
uv venv
uv pip install -e .
```

4. Run the program:
```bash
python main.py
```

On first run, it will open a browser window for Gmail authorization.

## Usage

1. The program will analyze up to 1000 promotional emails
2. It shows a list of senders sorted by number of emails sent
3. For each sender, starting with the most frequent, you can:
   - View their most recent email subject and preview
   - See the unsubscribe link if available
   - Choose to either:
     - Add them to ignore list (preserve their emails)
     - Delete all their emails (moves to trash)
4. Use 'q' at any time to quit the program

## Development

- Uses `uv` for dependency management
- `pytest` and `pytest-cov` for testing and coverage
- Format code using `black` and `isort`
- Type checking with `mypy`

## Files

- `main.py`: Main program logic
- `ignored_senders.json`: List of senders to preserve (created automatically)
- `token.pickle`: Gmail API credentials cache (created automatically)
- `credentials.json`: OAuth 2.0 credentials (you must provide this)

## Security Note

- `credentials.json` and `token.pickle` contain sensitive authentication data
- Both files are listed in `.gitignore` to prevent accidental commits
- Never share these files or commit them to version control 