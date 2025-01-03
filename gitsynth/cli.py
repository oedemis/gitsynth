import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from .core.git import GitHandler, GitHandlerError
from .core.ollama_handler import (
    OllamaHandler, DiffAnalysis,
    OllamaHandlerError
)
from .core.commit_types import COMMIT_TYPES
from typing import Dict, Any
import logging
import json
from .utils import console
import textwrap

from .core.commit_agent import CommitAgent, AgentState
import json
from langchain_core.messages import AIMessage
import os
from pathlib import Path

# Zwei separate Typer Apps
app = typer.Typer()
agent_app = typer.Typer()

# Die Apps zusammenführen
app.add_typer(agent_app, name="agent")

__all__ = ["app", "agent_app"]

def show_diff(diff: str):
    """Zeigt den Git Diff schön formatiert an"""
    syntax = Syntax(diff, "diff", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="[bold blue]Staged Changes"))

def format_file_changes(diff_analysis: DiffAnalysis) -> str:
    """Formatiert FileChanges für die Ausgabe"""
    try:
        result = []
        # Gruppiere nach Change Type
        changes_by_type = {
            "new": [],
            "modified": [],
            "deleted": [],
            "renamed": [],
            "mode_changed": []
        }
        
        # Gruppiere Dateien nach Change Type
        for file in diff_analysis.files:
            changes_by_type[file.change_type].append((
                f"• {file.file_path}\n"
                f"  └─ {file.changes}"
            ))
        
        # Füge Änderungen nach Typ hinzu
        for change_type, files in changes_by_type.items():
            if files:
                result.append(f"\n[bold cyan]{change_type.upper()} FILES:[/bold cyan]")
                result.extend(files)
        
        # Hauptänderungen
        result.extend([
            f"\n[bold yellow]MAIN CHANGE:[/bold yellow]",
            f"  {diff_analysis.main_change}",
            f"\n[bold yellow]RELATIONSHIPS:[/bold yellow]",
            f"  {diff_analysis.relationships}",
            f"\n[bold yellow]IMPACT:[/bold yellow]",
            f"  {diff_analysis.impact}"
        ])
        
        return "\n".join(result)
        
    except Exception as e:
        return f"[red]Error formatting changes: {str(e)}[/red]"

def format_commit_types(commit_types: Dict, selected_type: str) -> str:
    """Formatiert die Commit-Typen für die Anzeige"""
    return "\n".join([
        f"[bold green]• {k}:[/bold green] {v['description']} (Priority: {v['priority']})" 
        if k == selected_type else
        f"• {k}: {v['description']} (Priority: {v['priority']})"
        for k,v in commit_types.items()
    ])

def show_analysis_details(diff: str, analysis: Dict[str, Any]):
    """Zeigt detaillierte Analyse-Informationen"""
    # Diff anzeigen
    console.print("\n[bold blue]📝 Git Diff:[/bold blue]")
    syntax = Syntax(diff, "diff", theme="monokai", line_numbers=True)
    console.print(Panel(syntax))
    
    # Analyse-Details
    console.print(Panel(
        f"[bold]🔍 AI Analysis[/bold]\n"
        f"{format_file_changes(analysis['analysis'])}\n\n"
        f"[bold green]Commit Information:[/bold green]\n"
        f"• Type: [bold]{analysis['commit_type']}[/bold]\n"
        f"• Message: [bold]{analysis['commit_message']}[/bold]\n\n"
        f"[bold blue]Available Types:[/bold blue]\n"
        f"{format_commit_types(COMMIT_TYPES, analysis['commit_type'])}",
        title="[bold blue]Analysis Result",
        border_style="blue"
    ))

@app.command()
def commit(message: str = typer.Option(None, "--message", "-m", help="Optional commit message")):
    """Analyzes changes and creates an intelligent commit"""
    try:
        git = GitHandler()
        diff = git.get_staged_diff()
        show_diff(diff)
        
        if not message:
            console.print("[yellow]🤖 Analyzing changes...[/yellow]")
            llm = OllamaHandler()
            analysis = llm.analyze_diff(diff)
            
            show_analysis_details(diff, analysis)
            
            # Commit Message vorschlagen
            message = f"{analysis['commit_type']}: {analysis['commit_message']}"
            console.print(f"\n[green]💬 Suggested Commit Message:[/green] [bold]{message}[/bold]")
            
            if not typer.confirm("\nCreate commit with this message?", default=False):
                console.print("[yellow]Commit aborted by user[/yellow]")
                raise typer.Abort()
        
        commit_id = git.create_commit(message)
        console.print(f"[green]✓[/green] Created commit: [bold]{commit_id[:8]}[/bold]")
        
    except (GitHandlerError, OllamaHandlerError) as e:
        console.print(f"[red]✗ Error:[/red] {str(e)}")
        raise typer.Exit(1)

@app.command()
def analyze():
    """Analysiert Git-Änderungen mit AI"""
    try:
        git = GitHandler()
        diff = git.get_staged_diff()
        
        if not diff:
            console.print("[red]❌ Keine Änderungen im Staging-Bereich[/red]")
            raise typer.Exit(1)
        
        with console.status("[yellow]🤖 Analyzing changes...[/yellow]") as status:
            status.update("[yellow]1. Creating technical analysis...[/yellow]")
            llm = OllamaHandler()
            analysis = llm.analyze_diff(diff)
            
            status.update("[yellow]2. Formatting results...[/yellow]")
            show_analysis_details(diff, analysis)
        
    except (GitHandlerError, OllamaHandlerError) as e:
        console.print(f"[red]✗ Error:[/red] {str(e)}")
        raise typer.Exit(1)

@app.command()
def debug(
    diff: str = typer.Option(None, "--diff", "-d", help="Git diff string to analyze")
):
    """Debug-Modus: Zeigt das rohe LLM-Output"""
    try:
        if diff:
            # Nutze übergebenen Diff
            console.print("[yellow]🔍 Analysiere übergebenen Diff...[/yellow]")
            diff_text = diff
        else:
            # Nutze staged changes
            git_handler = GitHandler()
            diff_text = git_handler.get_staged_diff()
            
            if not diff_text:
                console.print("[red]❌ Keine Änderungen im Staging-Bereich gefunden.[/red]")
                raise typer.Exit(1)
                
        console.print("[yellow]🔍 Analysiere LLM Output...[/yellow]")
        llm_handler = OllamaHandler()
        result = llm_handler.debug_llm_output(diff_text)
        
        # Raw Analysis
        console.print("\n[bold blue]Raw Analysis:[/bold blue]")
        console.print(Panel(
            result.get("raw_output", "No output"),
            title="[bold]Technical Analysis"
        ))
        
        # Structured Output
        if result.get("structured_output"):
            console.print("\n[bold blue]Structured Analysis:[/bold blue]")
            console.print(Panel(
                Syntax(result["structured_output"], "json", theme="monokai"),
                title="[bold]DiffAnalysis Model"
            ))
            
            # Commit Information
            diff_analysis = json.loads(result["structured_output"])
            console.print("\n[bold blue]Commit Information:[/bold blue]")
            console.print(Panel(
                f"Type: [bold green]{diff_analysis['commit_type']}[/bold green]\n"
                f"Message: [bold]{diff_analysis['commit_message']}[/bold]",
                title="[bold]Commit Details"
            ))
        else:
            console.print("\n[red]❌ Structured Analysis failed[/red]")
        
    except Exception as e:
        console.print(f"[red]❌ Fehler: {str(e)}[/red]")
        raise typer.Exit(1)
    
###### Agent Commands ######

def format_proposal(proposal: dict) -> str:
    """Formatiert Commit-Vorschlag für die Ausgabe"""
    return f"""
Type: [bold cyan]{proposal['type']}[/bold cyan]
Scope: [bold yellow]{proposal['scope']}[/bold yellow]
Message: [bold green]{proposal['message']}[/bold green]
Breaking: {'Yes' if proposal['is_breaking'] else 'No'}

Changes:
{chr(10).join(f'• {c["file"]} ({c["change_type"]}): {c["description"]}' for c in proposal['changes'])}
"""

def format_changelog(changelog: dict) -> str:
    """Formatiert Changelog für die Ausgabe"""
    return changelog['content']

# Neuen Command hinzufügen:
@agent_app.command()
def commit(
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug output"),
    max_attempts: int = typer.Option(3, "--max-attempts", "-m", help="Maximum improvement attempts")
):
    """Intelligenter Commit mit strukturiertem Output"""
    try:
        git = GitHandler()
        diff = git.get_staged_diff()
        
        if not diff:
            console.print("[red]No staged changes found![/red]")
            raise typer.Exit(1)
            
        # Erstelle viz Ordner im aktuellen Verzeichnis
        current_dir = os.getcwd()
        viz_dir = os.path.join(current_dir, "viz")
        console.print(f"[yellow]Creating viz directory at: {viz_dir}[/yellow]")
        
        if not os.path.exists(viz_dir):
            os.makedirs(viz_dir)
            console.print(f"[green]Created viz directory[/green]")
        
        console.print("\n[bold blue]📝 Staged Changes:[/bold blue]")
        show_diff(diff)
            
        console.print("\n[bold cyan]🤖 Starting Analysis...[/bold cyan]")
        
        agent = CommitAgent()
        
        # Visualisiere den Workflow
        viz_path = os.path.join(viz_dir, "workflow.png")
        console.print(f"[yellow]Saving workflow to: {viz_path}[/yellow]")
        agent.visualize_workflow(viz_path)
        
        with console.status("[yellow]Analyzing changes...[/yellow]") as status:
            result = agent.stream([])
            
            for step in result:
                if debug:
                    console.print(f"\n[dim]Debug: Current step: {step}")
                
                if "messages" in step:
                    last_message = step["messages"][-1]
                    if isinstance(last_message, AIMessage):
                        console.print("\n[bold green]📊 Analysis Result:[/bold green]")
                        console.print(Panel(
                            last_message.content,
                            title="[bold blue]Technical Summary",
                            border_style="blue"
                        ))
            
        console.print("\n[bold green]✨ Analysis Complete![/bold green]")
            
    except GitHandlerError as e:
        console.print(f"[red]Git Error: {str(e)}[/red]")
        if debug:
            raise
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        if debug:
            raise
        raise typer.Exit(1)

if __name__ == "__main__":
    app()  # Jetzt handhabt app beide Command-Sets