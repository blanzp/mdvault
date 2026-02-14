#!/usr/bin/env python3
"""MDVault CLI - Manage your markdown note repository."""

import click
import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown

console = Console()

# Default vault location
DEFAULT_VAULT = Path.home() / ".mdvault"
CONFIG_FILE = ".mdvault.json"


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


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """MDVault - A CLI tool for managing markdown note repositories."""
    pass


@cli.command()
@click.argument("path", type=click.Path(), default=".")
def init(path):
    """Initialize a new vault in the specified directory."""
    vault_path = Path(path).resolve()
    config_path = vault_path / CONFIG_FILE
    
    if config_path.exists():
        console.print(f"[yellow]Vault already exists at {vault_path}[/yellow]")
        return
    
    vault_path.mkdir(parents=True, exist_ok=True)
    
    config = {
        "created": datetime.now().isoformat(),
        "version": "0.1.0",
        "default_template": None,
    }
    
    save_config(vault_path, config)
    console.print(f"[green]✓[/green] Initialized vault at {vault_path}")


@cli.command()
@click.argument("title")
@click.option("--tag", "-t", multiple=True, help="Add tags to the note")
@click.option("--template", help="Use a template")
def new(title, tag, template):
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
    }
    
    content = "---\n"
    for key, value in frontmatter.items():
        if isinstance(value, list):
            content += f"{key}:\n"
            for item in value:
                content += f"  - {item}\n"
        else:
            content += f"{key}: {value}\n"
    content += "---\n\n"
    content += f"# {title}\n\n"
    
    note_path.write_text(content)
    console.print(f"[green]✓[/green] Created note: {note_path}")
    
    # Open in editor if EDITOR is set
    editor = os.environ.get('EDITOR')
    if editor:
        os.system(f"{editor} {note_path}")


@cli.command()
@click.argument("query", required=False)
@click.option("--tag", "-t", help="Filter by tag")
def list(query, tag):
    """List all notes in the vault."""
    vault = ensure_vault()
    
    notes = []
    for md_file in vault.rglob("*.md"):
        if md_file.name.startswith('.'):
            continue
            
        content = md_file.read_text()
        
        # Extract frontmatter
        fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        title = md_file.stem.replace('-', ' ').title()
        tags_list = []
        created = None
        
        if fm_match:
            fm_text = fm_match.group(1)
            title_match = re.search(r'title:\s*(.+)', fm_text)
            if title_match:
                title = title_match.group(1).strip()
            
            tags_match = re.search(r'tags:\s*\n((?:\s*-\s*.+\n?)+)', fm_text)
            if tags_match:
                tags_list = [t.strip('- ').strip() for t in tags_match.group(1).split('\n') if t.strip()]
            
            created_match = re.search(r'created:\s*(.+)', fm_text)
            if created_match:
                created = created_match.group(1).strip()
        
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
@click.argument("query")
@click.option("--context", "-c", default=2, help="Lines of context to show")
def search(query, context):
    """Search for text in notes."""
    vault = ensure_vault()
    
    results = []
    for md_file in vault.rglob("*.md"):
        if md_file.name.startswith('.'):
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
    
    # Try exact path first
    note_path = vault / note
    if not note_path.exists():
        # Try with .md extension
        note_path = vault / f"{note}.md"
    
    if not note_path.exists():
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
    
    # Try exact path first
    note_path = vault / note
    if not note_path.exists():
        # Try with .md extension
        note_path = vault / f"{note}.md"
    
    if not note_path.exists():
        console.print(f"[red]Note not found: {note}[/red]")
        return
    
    os.system(f"{editor} {note_path}")


@cli.command()
def tags():
    """List all tags used in the vault."""
    vault = ensure_vault()
    
    tag_counts = {}
    for md_file in vault.rglob("*.md"):
        if md_file.name.startswith('.'):
            continue
        
        content = md_file.read_text()
        fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        
        if fm_match:
            fm_text = fm_match.group(1)
            tags_match = re.search(r'tags:\s*\n((?:\s*-\s*.+\n?)+)', fm_text)
            if tags_match:
                tags_list = [t.strip('- ').strip() for t in tags_match.group(1).split('\n') if t.strip()]
                for tag in tags_list:
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
    
    note_count = len(list(vault.rglob("*.md")))
    
    console.print(f"[cyan]Vault Location:[/cyan] {vault}")
    console.print(f"[cyan]Created:[/cyan] {config.get('created', 'Unknown')}")
    console.print(f"[cyan]Total Notes:[/cyan] {note_count}")
    console.print(f"[cyan]Version:[/cyan] {config.get('version', 'Unknown')}")


if __name__ == "__main__":
    cli()
