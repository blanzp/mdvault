# MDVault

A Python CLI tool for managing markdown note repositories — inspired by Obsidian CLI.

## Features

- 📝 Create and edit markdown notes
- 🔍 Search through your notes
- 🏷️ Tag management with frontmatter
- 📊 List and filter notes
- 🎨 Beautiful terminal UI with Rich
- 📂 Vault-based organization

## Installation

```bash
pip install -e .
```

Or install from source:

```bash
git clone https://github.com/blanzp/mdvault.git
cd mdvault
pip install -e .
```

## Quick Start

```bash
# Initialize a new vault
mdvault init ~/my-notes

# Navigate to your vault
cd ~/my-notes

# Create a new note
mdvault new "My First Note" -t ideas -t personal

# List all notes
mdvault list

# Search for content
mdvault search "keyword"

# Show a note in the terminal
mdvault show my-first-note

# Edit a note
mdvault edit my-first-note

# List all tags
mdvault tags

# View vault info
mdvault info
```

## Commands

### `mdvault init [PATH]`
Initialize a new vault in the specified directory (defaults to current directory).

### `mdvault new TITLE [OPTIONS]`
Create a new note with optional tags.

Options:
- `-t, --tag TAG` — Add tags (can be used multiple times)
- `--template TEMPLATE` — Use a template (coming soon)

### `mdvault list [QUERY] [OPTIONS]`
List all notes, optionally filtered by query or tag.

Options:
- `-t, --tag TAG` — Filter by tag

### `mdvault search QUERY [OPTIONS]`
Search for text across all notes.

Options:
- `-c, --context N` — Number of context lines to show (default: 2)

### `mdvault show NOTE`
Display a note in the terminal with markdown rendering.

### `mdvault edit NOTE`
Open a note in your default editor (`$EDITOR` or nano).

### `mdvault tags`
List all tags used in the vault with usage counts.

### `mdvault info`
Show vault information (location, note count, etc.).

## Note Format

Notes use YAML frontmatter for metadata:

```markdown
---
title: My Note Title
created: 2026-02-13T22:30:00
tags:
  - ideas
  - personal
---

# My Note Title

Your content goes here...
```

## Configuration

Each vault contains a `.mdvault.json` file with vault metadata. This file is automatically created during `mdvault init`.

## Requirements

- Python 3.8+
- click >= 8.0.0
- rich >= 10.0.0

## Development

```bash
# Clone the repo
git clone https://github.com/blanzp/mdvault.git
cd mdvault

# Install in development mode
pip install -e .

# Run tests (coming soon)
pytest
```

## Roadmap

- [ ] Templates for new notes
- [ ] Backlinks detection
- [ ] Graph visualization
- [ ] Export to other formats
- [ ] Sync with git
- [ ] Note linking syntax `[[note]]`
- [ ] Daily notes command

## License

MIT

## Author

Paul Blanz
