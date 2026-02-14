#!/usr/bin/env python3
"""MDVault CLI - Manage your markdown note repository."""

import click
import os
import sys
import re
import json
import random
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Set
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown

console = Console()

# Default vault location
DEFAULT_VAULT = Path.home() / ".mdvault"
CONFIG_FILE = ".mdvault.json"
ARCHIVE_DIR = ".archive"


def get_vault_root() -> Path:
    """Find the vault root by looking for .mdvault.json."""
    current = Path.cwd()
    while current != current.parent:
        if (current / CONFIG_FILE).exists():
            return current
        current = current.parent
    return None


def ensure_vault(vault_path: Optional[Path] = None) -> Path:
    """Ensure we're in a valid vault."""
    if vault_path:
        return vault_path
    
    vault = get_vault_root()
    if not vault:
        console.print("[red]Not in a vault. Run 'mdvault init' first.[/red]")
        sys.exit(1)
    return vault


def load_config(vault_path: Path) -> dict:
    """Load vault configuration."""
    config_path = vault_path / CONFIG_FILE
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}


def save_config(vault_path: Path, config: dict):
    """Save vault configuration."""
    config_path = vault_path / CONFIG_FILE
    config_path.write_text(json.dumps(config, indent=2))


def git_commit(vault_path: Path, message: str):
    """Auto-commit changes if git is enabled."""
    config = load_config(vault_path)
    if not config.get("auto_commit", False):
        return
    
    try:
        subprocess.run(["git", "-C", str(vault_path), "add", "."], capture_output=True)
        subprocess.run(["git", "-C", str(vault_path), "commit", "-m", message], capture_output=True)
    except Exception:
        pass  # Silent fail if git not available


def extract_frontmatter(content: str) -> tuple[dict, str]:
    """Extract frontmatter and body from markdown content."""
    fm_match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    if not fm_match:
        return {}, content
    
    fm_text = fm_match.group(1)
    body = fm_match.group(2)
    
    frontmatter = {}
    
    # Parse YAML-like frontmatter
    title_match = re.search(r'title:\s*(.+)', fm_text)
    if title_match:
        frontmatter['title'] = title_match.group(1).strip()
    
    created_match = re.search(r'created:\s*(.+)', fm_text)
    if created_match:
        frontmatter['created'] = created_match.group(1).strip()
    
    tags_match = re.search(r'tags:\s*\n((?:\s*-\s*.+\n?)+)', fm_text)
    if tags_match:
        frontmatter['tags'] = [t.strip('- ').strip() for t in tags_match.group(1).split('\n') if t.strip()]
    else:
        frontmatter['tags'] = []
    
    aliases_match = re.search(r'aliases:\s*\n((?:\s*-\s*.+\n?)+)', fm_text)
    if aliases_match:
        frontmatter['aliases'] = [a.strip('- ').strip() for a in aliases_match.group(1).split('\n') if a.strip()]
    else:
        frontmatter['aliases'] = []
    
    return frontmatter, body


def extract_wikilinks(content: str) -> Set[str]:
    """Extract all [[wikilinks]] from content."""
    return set(re.findall(r'\[\[([^\]]+)\]\]', content))


def find_note(vault: Path, name: str) -> Optional[Path]:
    """Find a note by name, alias, or filename."""
    # Try exact filename
    if (vault / f"{name}.md").exists():
        return vault / f"{name}.md"
    
    # Try slug match
    slug = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '-').lower()
    if (vault / f"{slug}.md").exists():
        return vault / f"{slug}.md"
    
    # Search by title or alias
    for md_file in vault.rglob("*.md"):
        if md_file.name.startswith('.'):
            continue
        content = md_file.read_text()
        fm, _ = extract_frontmatter(content)
        
        if fm.get('title', '').lower() == name.lower():
            return md_file
        
        if name.lower() in [a.lower() for a in fm.get('aliases', [])]:
            return md_file
    
    return None


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """MDVault - A CLI tool for managing markdown note repositories."""
    pass


@cli.command()
@click.argument("path", type=click.Path(), default=".")
@click.option("--auto-commit", is_flag=True, help="Enable git auto-commit")
def init(path, auto_commit):
    """Initialize a new vault in the specified directory."""
    vault_path = Path(path).resolve()
    config_path = vault_path / CONFIG_FILE
    
    if config_path.exists():
        console.print(f"[yellow]Vault already exists at {vault_path}[/yellow]")
        return
    
    vault_path.mkdir(parents=True, exist_ok=True)
    (vault_path / ARCHIVE_DIR).mkdir(exist_ok=True)
    
    config = {
        "created": datetime.now().isoformat(),
        "version": "0.1.0",
        "default_template": None,
        "auto_commit": auto_commit,
    }
    
    save_config(vault_path, config)
    
    # Initialize git if auto-commit enabled
    if auto_commit:
        try:
            subprocess.run(["git", "-C", str(vault_path), "init"], capture_output=True)
            subprocess.run(["git", "-C", str(vault_path), "config", "user.email", "vault@mdvault.local"], capture_output=True)
            subprocess.run(["git", "-C", str(vault_path), "config", "user.name", "MDVault"], capture_output=True)
            subprocess.run(["git", "-C", str(vault_path), "add", "."], capture_output=True)
            subprocess.run(["git", "-C", str(vault_path), "commit", "-m", "Initialize vault"], capture_output=True)
            console.print(f"[green]✓[/green] Initialized vault with git auto-commit at {vault_path}")
        except Exception:
            console.print(f"[yellow]Warning: Could not initialize git[/yellow]")
            console.print(f"[green]✓[/green] Initialized vault at {vault_path}")
    else:
        console.print(f"[green]✓[/green] Initialized vault at {vault_path}")


@cli.command()
@click.argument("title")
@click.option("--tag", "-t", multiple=True, help="Add tags to the note")
@click.option("--template", help="Use a template")
@click.option("--alias", "-a", multiple=True, help="Add aliases")
def new(title, tag, template, alias):
    """Create a new note."""
    vault = ensure_vault()
    
    # Sanitize filename
    filename = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')
    filename = re.sub(r'[-\s]+', '-', filename).lower()
    note_path = vault / f"{filename}.md"
    
    if note_path.exists():
        console.print(f"[yellow]Note already exists: {note_path}[/yellow]")
        return
    
    # Build frontmatter
    frontmatter = {
        "title": title,
        "created": datetime.now().isoformat(),
        "tags": list(tag) if tag else [],
        "aliases": list(alias) if alias else [],
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
    console.print(f"[green]✓[/green] Created note: {note_path}")
    
    git_commit(vault, f"Create note: {title}")
    
    # Open in editor if EDITOR is set
    editor = os.environ.get('EDITOR')
    if editor:
        os.system(f"{editor} {note_path}")


@cli.command()
@click.option("--edit", "-e", is_flag=True, help="Open in editor after creating")
def daily(edit):
    """Create or open today's daily note."""
    vault = ensure_vault()
    
    today = datetime.now().strftime("%Y-%m-%d")
    daily_dir = vault / "daily"
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
        console.print(f"[green]✓[/green] Created daily note: {note_path}")
        git_commit(vault, f"Daily note: {today}")
    else:
        console.print(f"[cyan]Opening daily note: {note_path}[/cyan]")
    
    if edit or os.environ.get('EDITOR'):
        editor = os.environ.get('EDITOR', 'nano')
        os.system(f"{editor} {note_path}")
    else:
        content = note_path.read_text()
        console.print(Markdown(content))


@cli.command()
@click.argument("query", required=False)
@click.option("--tag", "-t", help="Filter by tag")
def list(query, tag):
    """List all notes in the vault."""
    vault = ensure_vault()
    
    notes = []
    for md_file in vault.rglob("*.md"):
        if md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
            continue
            
        content = md_file.read_text()
        fm, body = extract_frontmatter(content)
        
        title = fm.get('title', md_file.stem.replace('-', ' ').title())
        tags_list = fm.get('tags', [])
        created = fm.get('created')
        
        # Filter by query
        if query and query.lower() not in title.lower() and query.lower() not in content.lower():
            continue
        
        # Filter by tag
        if tag and tag not in tags_list:
            continue
        
        notes.append({
            "path": md_file.relative_to(vault),
            "title": title,
            "tags": tags_list,
            "created": created,
            "modified": md_file.stat().st_mtime,
        })
    
    if not notes:
        console.print("[yellow]No notes found.[/yellow]")
        return
    
    # Display as table
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


@cli.command()
@click.option("--limit", "-n", default=10, help="Number of recent notes to show")
def recent(limit):
    """Show recently modified notes."""
    vault = ensure_vault()
    
    notes = []
    for md_file in vault.rglob("*.md"):
        if md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
            continue
        
        content = md_file.read_text()
        fm, _ = extract_frontmatter(content)
        title = fm.get('title', md_file.stem.replace('-', ' ').title())
        
        notes.append({
            "path": md_file.relative_to(vault),
            "title": title,
            "modified": md_file.stat().st_mtime,
        })
    
    if not notes:
        console.print("[yellow]No notes found.[/yellow]")
        return
    
    # Sort by modification time
    notes.sort(key=lambda n: n['modified'], reverse=True)
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Title", style="green")
    table.add_column("Modified", style="yellow")
    table.add_column("Path", style="dim")
    
    for note in notes[:limit]:
        mod_time = datetime.fromtimestamp(note['modified']).strftime("%Y-%m-%d %H:%M")
        table.add_row(note['title'], mod_time, str(note['path']))
    
    console.print(table)


@cli.command()
@click.option("--edit", "-e", is_flag=True, help="Open in editor")
def random(edit):
    """Open a random note."""
    vault = ensure_vault()
    
    notes = [md for md in vault.rglob("*.md") 
             if not md.name.startswith('.') and ARCHIVE_DIR not in str(md)]
    
    if not notes:
        console.print("[yellow]No notes found.[/yellow]")
        return
    
    note_path = random.choice(notes)
    content = note_path.read_text()
    fm, _ = extract_frontmatter(content)
    title = fm.get('title', note_path.stem)
    
    console.print(f"[cyan]Random note: {title}[/cyan]")
    console.print(f"[dim]{note_path.relative_to(vault)}[/dim]\n")
    
    if edit:
        editor = os.environ.get('EDITOR', 'nano')
        os.system(f"{editor} {note_path}")
    else:
        console.print(Markdown(content))


@cli.command()
@click.argument("query", required=False)
def find(query):
    """Fuzzy find notes using fzf (must be installed)."""
    vault = ensure_vault()
    
    # Check if fzf is available
    try:
        subprocess.run(["which", "fzf"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        console.print("[red]fzf not installed. Install with: brew install fzf or apt install fzf[/red]")
        return
    
    # Build note list
    notes = []
    for md_file in vault.rglob("*.md"):
        if md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
            continue
        content = md_file.read_text()
        fm, _ = extract_frontmatter(content)
        title = fm.get('title', md_file.stem.replace('-', ' ').title())
        rel_path = md_file.relative_to(vault)
        notes.append(f"{title} [{rel_path}]")
    
    if not notes:
        console.print("[yellow]No notes found.[/yellow]")
        return
    
    # Run fzf
    try:
        result = subprocess.run(
            ["fzf", "--height", "40%", "--reverse", "--query", query or ""],
            input="\n".join(notes),
            text=True,
            capture_output=True
        )
        
        if result.returncode == 0:
            selected = result.stdout.strip()
            # Extract path from selection
            path_match = re.search(r'\[(.*?)\]', selected)
            if path_match:
                note_path = vault / path_match.group(1)
                editor = os.environ.get('EDITOR', 'nano')
                os.system(f"{editor} {note_path}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.argument("note")
def backlinks(note):
    """Show notes that link to this note."""
    vault = ensure_vault()
    
    target_path = find_note(vault, note)
    if not target_path:
        console.print(f"[red]Note not found: {note}[/red]")
        return
    
    target_content = target_path.read_text()
    target_fm, _ = extract_frontmatter(target_content)
    target_title = target_fm.get('title', target_path.stem)
    target_slug = target_path.stem
    
    # Search for references
    backlinks = []
    for md_file in vault.rglob("*.md"):
        if md_file == target_path or md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
            continue
        
        content = md_file.read_text()
        links = extract_wikilinks(content)
        
        # Check if this note links to target
        if target_slug in links or target_title in links:
            fm, _ = extract_frontmatter(content)
            title = fm.get('title', md_file.stem.replace('-', ' ').title())
            backlinks.append({
                "title": title,
                "path": md_file.relative_to(vault)
            })
    
    if not backlinks:
        console.print(f"[yellow]No backlinks found for '{target_title}'[/yellow]")
        return
    
    console.print(f"[cyan]Backlinks to '{target_title}':[/cyan]\n")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Note", style="green")
    table.add_column("Path", style="dim")
    
    for link in backlinks:
        table.add_row(link['title'], str(link['path']))
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(backlinks)} backlinks[/dim]")


@cli.command()
@click.argument("old_name")
@click.argument("new_name")
@click.option("--update-links", is_flag=True, default=True, help="Update wikilinks in other notes")
def mv(old_name, new_name, update_links):
    """Rename a note and optionally update all links to it."""
    vault = ensure_vault()
    
    old_path = find_note(vault, old_name)
    if not old_path:
        console.print(f"[red]Note not found: {old_name}[/red]")
        return
    
    # Generate new filename
    new_filename = re.sub(r'[^\w\s-]', '', new_name).strip().replace(' ', '-').lower()
    new_path = vault / f"{new_filename}.md"
    
    if new_path.exists():
        console.print(f"[red]Target already exists: {new_path}[/red]")
        return
    
    # Update title in frontmatter
    content = old_path.read_text()
    fm, body = extract_frontmatter(content)
    fm['title'] = new_name
    
    # Rebuild content
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
    
    # Update links in other notes
    if update_links:
        old_slug = old_path.stem
        new_slug = new_path.stem
        
        updated_count = 0
        for md_file in vault.rglob("*.md"):
            if md_file == new_path or md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
                continue
            
            content = md_file.read_text()
            if f"[[{old_slug}]]" in content or f"[[{old_name}]]" in content:
                content = content.replace(f"[[{old_slug}]]", f"[[{new_slug}]]")
                content = content.replace(f"[[{old_name}]]", f"[[{new_name}]]")
                md_file.write_text(content)
                updated_count += 1
        
        if updated_count:
            console.print(f"[green]✓[/green] Updated links in {updated_count} notes")
    
    old_path.unlink()
    console.print(f"[green]✓[/green] Renamed: {old_name} → {new_name}")
    
    git_commit(vault, f"Rename: {old_name} → {new_name}")


@cli.command()
@click.argument("note")
def archive(note):
    """Move a note to the archive."""
    vault = ensure_vault()
    
    note_path = find_note(vault, note)
    if not note_path:
        console.print(f"[red]Note not found: {note}[/red]")
        return
    
    archive_dir = vault / ARCHIVE_DIR
    archive_dir.mkdir(exist_ok=True)
    
    archive_path = archive_dir / note_path.name
    note_path.rename(archive_path)
    
    console.print(f"[green]✓[/green] Archived: {note_path.name}")
    git_commit(vault, f"Archive: {note_path.stem}")


@cli.command()
@click.argument("query")
@click.option("--context", "-c", default=2, help="Lines of context to show")
def search(query, context):
    """Search for text in notes."""
    vault = ensure_vault()
    
    results = []
    for md_file in vault.rglob("*.md"):
        if md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
            continue
        
        content = md_file.read_text()
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if query.lower() in line.lower():
                start = max(0, i - context)
                end = min(len(lines), i + context + 1)
                context_lines = lines[start:end]
                
                results.append({
                    "path": md_file.relative_to(vault),
                    "line": i + 1,
                    "context": '\n'.join(context_lines),
                })
    
    if not results:
        console.print(f"[yellow]No results found for '{query}'[/yellow]")
        return
    
    for result in results:
        console.print(f"\n[cyan]{result['path']}:{result['line']}[/cyan]")
        console.print(result['context'])
    
    console.print(f"\n[dim]Found {len(results)} matches[/dim]")


@cli.command()
@click.argument("note")
def show(note):
    """Display a note in the terminal."""
    vault = ensure_vault()
    
    note_path = find_note(vault, note)
    if not note_path:
        console.print(f"[red]Note not found: {note}[/red]")
        return
    
    content = note_path.read_text()
    md = Markdown(content)
    console.print(md)


@cli.command()
@click.argument("note")
def edit(note):
    """Open a note in your default editor."""
    vault = ensure_vault()
    editor = os.environ.get('EDITOR', 'nano')
    
    note_path = find_note(vault, note)
    if not note_path:
        console.print(f"[red]Note not found: {note}[/red]")
        return
    
    os.system(f"{editor} {note_path}")
    git_commit(vault, f"Edit: {note_path.stem}")


@cli.command()
def tags():
    """List all tags used in the vault."""
    vault = ensure_vault()
    
    tag_counts = {}
    for md_file in vault.rglob("*.md"):
        if md_file.name.startswith('.') or ARCHIVE_DIR in str(md_file):
            continue
        
        content = md_file.read_text()
        fm, _ = extract_frontmatter(content)
        
        for tag in fm.get('tags', []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    if not tag_counts:
        console.print("[yellow]No tags found.[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Tag", style="yellow")
    table.add_column("Count", style="green", justify="right")
    
    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
        table.add_row(tag, str(count))
    
    console.print(table)


@cli.command()
def info():
    """Show vault information."""
    vault = ensure_vault()
    config = load_config(vault)
    
    note_count = len([md for md in vault.rglob("*.md") 
                      if not md.name.startswith('.') and ARCHIVE_DIR not in str(md)])
    archive_count = len(list((vault / ARCHIVE_DIR).glob("*.md")))
    
    console.print(f"[cyan]Vault Location:[/cyan] {vault}")
    console.print(f"[cyan]Created:[/cyan] {config.get('created', 'Unknown')}")
    console.print(f"[cyan]Total Notes:[/cyan] {note_count}")
    console.print(f"[cyan]Archived:[/cyan] {archive_count}")
    console.print(f"[cyan]Auto-commit:[/cyan] {'Enabled' if config.get('auto_commit') else 'Disabled'}")
    console.print(f"[cyan]Version:[/cyan] {config.get('version', 'Unknown')}")


if __name__ == "__main__":
    cli()
