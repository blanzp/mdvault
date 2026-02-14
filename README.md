# MDVault

A Python CLI tool for managing markdown note repositories — inspired by Obsidian CLI.

## Features

- 🐚 **Interactive Shell** — REPL-style interface with `/` commands and tab completion
- 📝 Create and edit markdown notes
- 📅 **Daily notes** — automatic date-based notes
- 🔗 **Wiki-style links** — `[[note]]` syntax support
- ⬅️ **Backlinks** — see what links to each note
- 🔍 Search through your notes
- 🎯 **Fuzzy finder** — interactive note picker with fzf
- 🏷️ Tag management with frontmatter
- 🔄 **Git auto-commit** — version control built-in
- 🕒 **Recent notes** — see what you've been working on
- 🎲 **Random note** — rediscover old notes
- ✏️ **Rename with link updates** — change names without breaking links
- 🗃️ **Archive** — soft-delete to `.archive/`
- 🏷️ **Aliases** — multiple names for the same note
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

# Or with git auto-commit
mdvault init ~/my-notes --auto-commit

# Navigate to your vault
cd ~/my-notes

# Start interactive shell (recommended!)
mdvault shell

# Or use individual commands:

# Create today's daily note
mdvault daily

# Create a new note
mdvault new "My First Note" -t ideas -t personal -a "first note"

# List all notes
mdvault list

# Show recent notes
mdvault recent

# Open a random note
mdvault random

# Fuzzy find a note (requires fzf)
mdvault find

# Search for content
mdvault search "keyword"

# Show backlinks to a note
mdvault backlinks "My First Note"

# Rename a note (updates all links)
mdvault mv "My First Note" "My Renamed Note"

# Archive a note
mdvault archive "old-note"

# Show a note in the terminal
mdvault show my-first-note

# Edit a note
mdvault edit my-first-note

# List all tags
mdvault tags

# View vault info
mdvault info
```

## Interactive Shell

MDVault includes an interactive shell mode with tab completion and type-ahead, similar to Claude's code experience:

```bash
cd ~/my-notes
mdvault shell
```

Inside the shell, use `/` commands:

```
mdvault> /new "My Note" -t ideas
✓ Created: My Note

mdvault> /list
┏━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┓
┃ Title   ┃ Tags  ┃ Path       ┃
┡━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━┩
│ My Note │ ideas │ my-note.md │
└─────────┴───────┴────────────┘

mdvault> /show "My Note"
# My Note

mdvault> /exit
Goodbye!
```

**Features:**
- Tab completion for commands and note names
- Command history (up/down arrows)
- Type-ahead suggestions
- All standard commands work with `/` prefix

**Available Shell Commands:**
- `/new <title> [-t tag]` — Create note
- `/daily` — Today's note
- `/list [query]` — List notes
- `/recent [n]` — Recent notes
- `/random` — Random note
- `/search <query>` — Search
- `/show <note>` — Display note
- `/edit <note>` — Edit in $EDITOR
- `/backlinks <note>` — Show backlinks
- `/mv <old> <new>` — Rename
- `/archive <note>` — Archive
- `/tags` — List tags
- `/info` — Vault info
- `/help` — Show help
- `/exit` — Quit shell

## Commands

### `mdvault shell`
Start the interactive shell mode. Recommended for regular use!

### `mdvault init [PATH] [OPTIONS]`
Initialize a new vault in the specified directory (defaults to current directory).

Options:
- `--auto-commit` — Enable git auto-commit for all changes

### `mdvault new TITLE [OPTIONS]`
Create a new note with optional tags and aliases.

Options:
- `-t, --tag TAG` — Add tags (can be used multiple times)
- `-a, --alias ALIAS` — Add aliases (can be used multiple times)
- `--template TEMPLATE` — Use a template (coming soon)

### `mdvault daily [OPTIONS]`
Create or open today's daily note (YYYY-MM-DD format in `daily/` folder).

Options:
- `-e, --edit` — Open in editor immediately

### `mdvault list [QUERY] [OPTIONS]`
List all notes, optionally filtered by query or tag.

Options:
- `-t, --tag TAG` — Filter by tag

### `mdvault recent [OPTIONS]`
Show recently modified notes.

Options:
- `-n, --limit N` — Number of notes to show (default: 10)

### `mdvault random [OPTIONS]`
Open a random note from your vault.

Options:
- `-e, --edit` — Open in editor

### `mdvault find [QUERY]`
Fuzzy find notes using fzf (must be installed separately).

Requires: `brew install fzf` or `apt install fzf`

### `mdvault backlinks NOTE`
Show all notes that link to the specified note (via `[[wikilinks]]`).

### `mdvault mv OLD_NAME NEW_NAME [OPTIONS]`
Rename a note and update all wikilinks pointing to it.

Options:
- `--update-links` — Update references in other notes (default: true)

### `mdvault archive NOTE`
Move a note to `.archive/` directory (soft delete).

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
aliases:
  - alternate name
  - another alias
---

# My Note Title

Your content goes here...

Link to other notes with [[note-name]] or [[Note Title]].
```

## Wiki-Style Links

Use `[[note-name]]` or `[[Note Title]]` to link between notes:

```markdown
I was reading [[my-research]] and thought about [[Future Ideas]].
```

Links work with:
- File names (without .md): `[[my-note]]`
- Note titles: `[[My Note Title]]`
- Aliases: `[[alternate name]]`

Use `mdvault backlinks <note>` to see what links to a note.

## Daily Notes

Daily notes are automatically created in the `daily/` folder with YYYY-MM-DD naming:

```bash
# Create or open today's note
mdvault daily

# Opens in editor if $EDITOR is set, or with -e flag
mdvault daily -e
```

Daily notes include a template with Notes, Tasks, and Links sections.

## Git Auto-Commit

Enable git auto-commit during init:

```bash
mdvault init --auto-commit
```

Every note create/edit/rename/archive will be automatically committed with a descriptive message.

## Fuzzy Finder

Install `fzf` for interactive note selection:

```bash
# macOS
brew install fzf

# Ubuntu/Debian
sudo apt install fzf

# Then use
mdvault find
```

Type to filter, arrow keys to select, Enter to open in editor.

## Configuration

Each vault contains a `.mdvault.json` file with vault metadata:

```json
{
  "created": "2026-02-13T22:30:00",
  "version": "0.1.0",
  "default_template": null,
  "auto_commit": true
}
```

## Requirements

- Python 3.8+
- click >= 8.0.0
- rich >= 10.0.0
- prompt-toolkit >= 3.0.0
- fzf (optional, for `mdvault find`)
- git (optional, for auto-commit)

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

- [x] Daily notes
- [x] Wiki-style links `[[note]]`
- [x] Backlinks
- [x] Fuzzy finder (fzf)
- [x] Git auto-commit
- [x] Recent notes
- [x] Random note
- [x] Rename with link updates
- [x] Archive (soft delete)
- [x] Aliases
- [ ] Templates for new notes
- [ ] Full-text index (SQLite FTS)
- [ ] Graph visualization
- [ ] Export to other formats (PDF, HTML)
- [ ] Stats dashboard
- [ ] Note linking in editor preview

## License

MIT

## Author

Paul Blanz
