"""Interactive shell for MDVault."""

import os
import sys
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from mdvault.cli import (
    ensure_vault,
    load_config,
    find_note,
    extract_frontmatter,
    extract_wikilinks,
    git_commit,
    ARCHIVE_DIR,
)
from datetime import datetime
import re
import random as random_module

console = Console()


class VaultCompleter(Completer):
    """Autocompleter for vault commands and note names."""
    
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.commands = [
            '/new', '/daily', '/list', '/recent', '/random', '/find',
            '/search', '/show', '/edit', '/backlinks', '/mv', '/archive',
            '/tags', '/info', '/help', '/exit', '/quit'
        ]
    
    def get_note_names(self):
        """Get all note names in the vault."""
        notes = []
        for md_file in self.vault_path.rglob("*.md"):
            if md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
                continue
            content = md_file.read_text()
            fm, _ = extract_frontmatter(content)
            title = fm.get('title', md_file.stem.replace('-', ' ').title())
            notes.append(title)
        return notes
    
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        
        # Command completion
        if text.startswith('/'):
            for cmd in self.commands:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))
        
        # Note name completion for certain commands
        elif any(text.startswith(cmd + ' ') for cmd in ['/show', '/edit', '/backlinks', '/mv', '/archive']):
            # Extract the partial note name
            parts = text.split(' ', 1)
            if len(parts) > 1:
                partial = parts[1]
                for note_name in self.get_note_names():
                    if partial.lower() in note_name.lower():
                        yield Completion(note_name, start_position=-len(partial))


style = Style.from_dict({
    'prompt': '#00aa00 bold',
})


class VaultShell:
    """Interactive shell for MDVault."""
    
    def __init__(self, vault_path: Path):
        self.vault = vault_path
        self.session = PromptSession(
            history=InMemoryHistory(),
            completer=VaultCompleter(vault_path),
            style=style,
            complete_while_typing=True,
        )
        self.running = True
    
    def run(self):
        """Start the interactive shell."""
        config = load_config(self.vault)
        console.print(f"[cyan]MDVault Shell[/cyan] - {self.vault}")
        console.print("[dim]Type /help for commands, /exit to quit[/dim]\n")
        
        while self.running:
            try:
                text = self.session.prompt('mdvault> ', style=style)
                text = text.strip()
                
                if not text:
                    continue
                
                self.handle_command(text)
                
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
        
        console.print("\n[dim]Goodbye![/dim]")
    
    def handle_command(self, text: str):
        """Handle a command input."""
        if not text.startswith('/'):
            console.print("[yellow]Commands must start with /. Type /help for available commands.[/yellow]")
            return
        
        parts = text.split(maxsplit=1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        
        handlers = {
            '/help': self.cmd_help,
            '/exit': self.cmd_exit,
            '/quit': self.cmd_exit,
            '/new': self.cmd_new,
            '/daily': self.cmd_daily,
            '/list': self.cmd_list,
            '/recent': self.cmd_recent,
            '/random': self.cmd_random,
            '/search': self.cmd_search,
            '/show': self.cmd_show,
            '/edit': self.cmd_edit,
            '/backlinks': self.cmd_backlinks,
            '/mv': self.cmd_mv,
            '/archive': self.cmd_archive,
            '/tags': self.cmd_tags,
            '/info': self.cmd_info,
        }
        
        handler = handlers.get(cmd)
        if handler:
            handler(args)
        else:
            console.print(f"[red]Unknown command: {cmd}[/red]")
            console.print("[dim]Type /help for available commands[/dim]")
    
    def cmd_help(self, args):
        """Show help."""
        help_text = """
[cyan]Available Commands:[/cyan]

  [green]/new <title> [-t tag1 -t tag2][/green]
    Create a new note

  [green]/daily[/green]
    Create or open today's daily note

  [green]/list [query] [-t tag][/green]
    List all notes (optionally filtered)

  [green]/recent [n][/green]
    Show recently modified notes

  [green]/random[/green]
    Open a random note

  [green]/search <query>[/green]
    Search for text in notes

  [green]/show <note>[/green]
    Display a note

  [green]/edit <note>[/green]
    Open note in editor

  [green]/backlinks <note>[/green]
    Show notes linking to this note

  [green]/mv <old> <new>[/green]
    Rename a note (updates links)

  [green]/archive <note>[/green]
    Archive a note

  [green]/tags[/green]
    List all tags

  [green]/info[/green]
    Show vault information

  [green]/help[/green]
    Show this help

  [green]/exit, /quit[/green]
    Exit the shell

[dim]Press Tab for autocomplete on commands and note names[/dim]
"""
        console.print(help_text)
    
    def cmd_exit(self, args):
        """Exit the shell."""
        self.running = False
    
    def cmd_new(self, args):
        """Create a new note."""
        if not args:
            console.print("[yellow]Usage: /new <title> [-t tag1 -t tag2] [-a alias1][/yellow]")
            return
        
        # Parse args
        import shlex
        try:
            parts = shlex.split(args)
        except ValueError:
            parts = args.split()
        
        if not parts:
            console.print("[yellow]Please provide a note title[/yellow]")
            return
        
        title = parts[0]
        tags = []
        aliases = []
        
        i = 1
        while i < len(parts):
            if parts[i] == '-t' and i + 1 < len(parts):
                tags.append(parts[i + 1])
                i += 2
            elif parts[i] == '-a' and i + 1 < len(parts):
                aliases.append(parts[i + 1])
                i += 2
            else:
                i += 1
        
        # Create note
        filename = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')
        filename = re.sub(r'[-\s]+', '-', filename).lower()
        note_path = self.vault / f"{filename}.md"
        
        if note_path.exists():
            console.print(f"[yellow]Note already exists: {note_path}[/yellow]")
            return
        
        frontmatter = {
            "title": title,
            "created": datetime.now().isoformat(),
            "tags": tags,
            "aliases": aliases,
        }
        
        content = "---\n"
        for key, value in frontmatter.items():
            if isinstance(value, list) and value:
                content += f"{key}:\n"
                for item in value:
                    content += f"  - {item}\n"
            elif not isinstance(value, list):
                content += f"{key}: {value}\n"
        content += "---\n\n"
        content += f"# {title}\n\n"
        
        note_path.write_text(content)
        console.print(f"[green]✓[/green] Created: {title}")
        git_commit(self.vault, f"Create note: {title}")
    
    def cmd_daily(self, args):
        """Create or open today's daily note."""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_dir = self.vault / "daily"
        daily_dir.mkdir(exist_ok=True)
        
        note_path = daily_dir / f"{today}.md"
        
        if not note_path.exists():
            content = f"""---
title: {today}
created: {datetime.now().isoformat()}
tags:
  - daily
---

# {today}

## Notes

## Tasks

- [ ] 

## Links

"""
            note_path.write_text(content)
            console.print(f"[green]✓[/green] Created daily note: {today}")
            git_commit(self.vault, f"Daily note: {today}")
        
        content = note_path.read_text()
        console.print(f"\n[cyan]Daily Note: {today}[/cyan]")
        console.print(Markdown(content))
    
    def cmd_list(self, args):
        """List all notes."""
        notes = []
        query = None
        tag_filter = None
        
        # Simple arg parsing
        if args:
            parts = args.split()
            if '-t' in parts:
                tag_idx = parts.index('-t')
                if tag_idx + 1 < len(parts):
                    tag_filter = parts[tag_idx + 1]
                    query = ' '.join(parts[:tag_idx])
            else:
                query = args
        
        for md_file in self.vault.rglob("*.md"):
            if md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
                continue
            
            content = md_file.read_text()
            fm, body = extract_frontmatter(content)
            
            title = fm.get('title', md_file.stem.replace('-', ' ').title())
            tags_list = fm.get('tags', [])
            
            if query and query.lower() not in title.lower() and query.lower() not in content.lower():
                continue
            
            if tag_filter and tag_filter not in tags_list:
                continue
            
            notes.append({
                "path": md_file.relative_to(self.vault),
                "title": title,
                "tags": tags_list,
            })
        
        if not notes:
            console.print("[yellow]No notes found[/yellow]")
            return
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Title", style="green")
        table.add_column("Tags", style="yellow")
        table.add_column("Path", style="dim")
        
        for note in sorted(notes, key=lambda n: n['title']):
            table.add_row(
                note['title'],
                ', '.join(note['tags']) if note['tags'] else '',
                str(note['path'])
            )
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(notes)} notes[/dim]")
    
    def cmd_recent(self, args):
        """Show recent notes."""
        limit = 10
        if args:
            try:
                limit = int(args)
            except ValueError:
                pass
        
        notes = []
        for md_file in self.vault.rglob("*.md"):
            if md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
                continue
            
            content = md_file.read_text()
            fm, _ = extract_frontmatter(content)
            title = fm.get('title', md_file.stem.replace('-', ' ').title())
            
            notes.append({
                "path": md_file.relative_to(self.vault),
                "title": title,
                "modified": md_file.stat().st_mtime,
            })
        
        if not notes:
            console.print("[yellow]No notes found[/yellow]")
            return
        
        notes.sort(key=lambda n: n['modified'], reverse=True)
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Title", style="green")
        table.add_column("Modified", style="yellow")
        table.add_column("Path", style="dim")
        
        for note in notes[:limit]:
            mod_time = datetime.fromtimestamp(note['modified']).strftime("%Y-%m-%d %H:%M")
            table.add_row(note['title'], mod_time, str(note['path']))
        
        console.print(table)
    
    def cmd_random(self, args):
        """Show a random note."""
        notes = [md for md in self.vault.rglob("*.md")
                 if not md.name.startswith('.') and ARCHIVE_DIR not in str(md)]
        
        if not notes:
            console.print("[yellow]No notes found[/yellow]")
            return
        
        note_path = random_module.choice(notes)
        content = note_path.read_text()
        fm, _ = extract_frontmatter(content)
        title = fm.get('title', note_path.stem)
        
        console.print(f"\n[cyan]Random: {title}[/cyan]")
        console.print(f"[dim]{note_path.relative_to(self.vault)}[/dim]\n")
        console.print(Markdown(content))
    
    def cmd_search(self, args):
        """Search notes."""
        if not args:
            console.print("[yellow]Usage: /search <query>[/yellow]")
            return
        
        results = []
        for md_file in self.vault.rglob("*.md"):
            if md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
                continue
            
            content = md_file.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if args.lower() in line.lower():
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    context_lines = lines[start:end]
                    
                    results.append({
                        "path": md_file.relative_to(self.vault),
                        "line": i + 1,
                        "context": '\n'.join(context_lines),
                    })
        
        if not results:
            console.print(f"[yellow]No results found for '{args}'[/yellow]")
            return
        
        for result in results:
            console.print(f"\n[cyan]{result['path']}:{result['line']}[/cyan]")
            console.print(result['context'])
        
        console.print(f"\n[dim]Found {len(results)} matches[/dim]")
    
    def cmd_show(self, args):
        """Show a note."""
        if not args:
            console.print("[yellow]Usage: /show <note>[/yellow]")
            return
        
        note_path = find_note(self.vault, args)
        if not note_path:
            console.print(f"[red]Note not found: {args}[/red]")
            return
        
        content = note_path.read_text()
        console.print(f"\n[cyan]{note_path.relative_to(self.vault)}[/cyan]\n")
        console.print(Markdown(content))
    
    def cmd_edit(self, args):
        """Edit a note."""
        if not args:
            console.print("[yellow]Usage: /edit <note>[/yellow]")
            return
        
        note_path = find_note(self.vault, args)
        if not note_path:
            console.print(f"[red]Note not found: {args}[/red]")
            return
        
        editor = os.environ.get('EDITOR', 'nano')
        os.system(f"{editor} {note_path}")
        console.print(f"[green]✓[/green] Edited: {note_path.stem}")
        git_commit(self.vault, f"Edit: {note_path.stem}")
    
    def cmd_backlinks(self, args):
        """Show backlinks."""
        if not args:
            console.print("[yellow]Usage: /backlinks <note>[/yellow]")
            return
        
        target_path = find_note(self.vault, args)
        if not target_path:
            console.print(f"[red]Note not found: {args}[/red]")
            return
        
        target_content = target_path.read_text()
        target_fm, _ = extract_frontmatter(target_content)
        target_title = target_fm.get('title', target_path.stem)
        target_slug = target_path.stem
        
        backlinks = []
        for md_file in self.vault.rglob("*.md"):
            if md_file == target_path or md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
                continue
            
            content = md_file.read_text()
            links = extract_wikilinks(content)
            
            if target_slug in links or target_title in links:
                fm, _ = extract_frontmatter(content)
                title = fm.get('title', md_file.stem.replace('-', ' ').title())
                backlinks.append({
                    "title": title,
                    "path": md_file.relative_to(self.vault)
                })
        
        if not backlinks:
            console.print(f"[yellow]No backlinks found for '{target_title}'[/yellow]")
            return
        
        console.print(f"\n[cyan]Backlinks to '{target_title}':[/cyan]\n")
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Note", style="green")
        table.add_column("Path", style="dim")
        
        for link in backlinks:
            table.add_row(link['title'], str(link['path']))
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(backlinks)} backlinks[/dim]")
    
    def cmd_mv(self, args):
        """Rename a note."""
        if not args:
            console.print("[yellow]Usage: /mv <old> <new>[/yellow]")
            return
        
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            console.print("[yellow]Please provide both old and new names[/yellow]")
            return
        
        old_name, new_name = parts[0], parts[1]
        
        old_path = find_note(self.vault, old_name)
        if not old_path:
            console.print(f"[red]Note not found: {old_name}[/red]")
            return
        
        new_filename = re.sub(r'[^\w\s-]', '', new_name).strip().replace(' ', '-').lower()
        new_path = self.vault / f"{new_filename}.md"
        
        if new_path.exists():
            console.print(f"[red]Target already exists: {new_path}[/red]")
            return
        
        # Update frontmatter
        content = old_path.read_text()
        fm, body = extract_frontmatter(content)
        fm['title'] = new_name
        
        new_content = "---\n"
        for key, value in fm.items():
            if isinstance(value, list) and value:
                new_content += f"{key}:\n"
                for item in value:
                    new_content += f"  - {item}\n"
            elif not isinstance(value, list):
                new_content += f"{key}: {value}\n"
        new_content += "---\n" + body
        
        new_path.write_text(new_content)
        
        # Update links
        old_slug = old_path.stem
        new_slug = new_path.stem
        
        updated_count = 0
        for md_file in self.vault.rglob("*.md"):
            if md_file == new_path or md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
                continue
            
            content = md_file.read_text()
            if f"[[{old_slug}]]" in content or f"[[{old_name}]]" in content:
                content = content.replace(f"[[{old_slug}]]", f"[[{new_slug}]]")
                content = content.replace(f"[[{old_name}]]", f"[[{new_name}]]")
                md_file.write_text(content)
                updated_count += 1
        
        old_path.unlink()
        
        if updated_count:
            console.print(f"[green]✓[/green] Updated links in {updated_count} notes")
        console.print(f"[green]✓[/green] Renamed: {old_name} → {new_name}")
        git_commit(self.vault, f"Rename: {old_name} → {new_name}")
    
    def cmd_archive(self, args):
        """Archive a note."""
        if not args:
            console.print("[yellow]Usage: /archive <note>[/yellow]")
            return
        
        note_path = find_note(self.vault, args)
        if not note_path:
            console.print(f"[red]Note not found: {args}[/red]")
            return
        
        archive_dir = self.vault / ARCHIVE_DIR
        archive_dir.mkdir(exist_ok=True)
        
        archive_path = archive_dir / note_path.name
        note_path.rename(archive_path)
        
        console.print(f"[green]✓[/green] Archived: {note_path.name}")
        git_commit(self.vault, f"Archive: {note_path.stem}")
    
    def cmd_tags(self, args):
        """List all tags."""
        tag_counts = {}
        for md_file in self.vault.rglob("*.md"):
            if md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
                continue
            
            content = md_file.read_text()
            fm, _ = extract_frontmatter(content)
            
            for tag in fm.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        if not tag_counts:
            console.print("[yellow]No tags found[/yellow]")
            return
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Tag", style="yellow")
        table.add_column("Count", style="green", justify="right")
        
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
            table.add_row(tag, str(count))
        
        console.print(table)
    
    def cmd_info(self, args):
        """Show vault info."""
        config = load_config(self.vault)
        
        note_count = len([md for md in self.vault.rglob("*.md")
                          if not md.name.startswith('.') and ARCHIVE_DIR not in str(md)])
        archive_count = len(list((self.vault / ARCHIVE_DIR).glob("*.md")))
        
        console.print(f"\n[cyan]Vault Location:[/cyan] {self.vault}")
        console.print(f"[cyan]Created:[/cyan] {config.get('created', 'Unknown')}")
        console.print(f"[cyan]Total Notes:[/cyan] {note_count}")
        console.print(f"[cyan]Archived:[/cyan] {archive_count}")
        console.print(f"[cyan]Auto-commit:[/cyan] {'Enabled' if config.get('auto_commit') else 'Disabled'}")
        console.print(f"[cyan]Version:[/cyan] {config.get('version', 'Unknown')}\n")


def start_shell():
    """Start the interactive shell."""
    try:
        vault = ensure_vault()
    except SystemExit:
        console.print("[red]Not in a vault. Run 'mdvault init' first.[/red]")
        return
    
    shell = VaultShell(vault)
    shell.run()
