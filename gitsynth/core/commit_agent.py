"""
GitSynth Commit Agent - Ein intelligenter Helfer für Git Commits
--------------------------------------------------------------

Was macht das hier?
- Wir bauen einen "Workflow" (wie eine Kette von Aktionen) für Git Commits
- Der Agent analysiert Änderungen und hilft bessere Commit Messages zu schreiben
- Er nutzt KI (Large Language Models) für die Analyse

Wie funktioniert das?
1. Git Diff holen (was wurde geändert?)
2. Änderungen analysieren (was bedeuten die Änderungen?)
3. Commit Message vorschlagen
4. Qualität prüfen
5. Bei Bedarf verbessern
"""

from typing import Annotated, Sequence, List, Optional, Literal, Any, Dict
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
import ollama
import os
from .git import GitHandler, GitHandlerError
from unidiff import PatchSet, PatchedFile
from io import StringIO
import json
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from langchain_core.runnables.graph import MermaidDrawMethod  # Neuer Import
from pathlib import Path

console = Console()


######################################################################################################
# Pydantic Models


class GitFileChange(BaseModel):
    """Detailed analysis of a single file change"""
    path: str
    change_type: Literal["NEW", "DELETED", "RENAMED", "MODE_CHANGED", "MODIFIED", "BINARY", "SUBMODULE", "CONFLICT"]
    old_path: Optional[str] = None
    added_lines: int = 0
    removed_lines: int = 0
    hunks: List[dict] = Field(default_factory=list)
    purpose: str = Field(description="Description of what changed and why")

class GitDiffAnalysis(BaseModel):
    """Structured Analysis of Git Changes"""
    summary: str = Field(description="Brief technical summary of all changes")
    change_type: Literal["feat", "fix", "docs", "refactor", "test", "chore", "style", "perf"]
    files: List[GitFileChange]
    breaking_change: bool = Field(default=False)

class ConventionalCommit(BaseModel):
    """Structured Conventional Commit Message"""
    type: Literal["feat", "fix", "docs", "refactor", "test", "chore", "style", "perf"]
    scope: Optional[str] = None
    description: str = Field(description="Imperative description of the change")
    breaking: bool = False
    body: Optional[str] = None
    footer: Optional[str] = None

class CommitQuality(BaseModel):
    """Binary Quality Check Result"""
    is_valid: bool

## Agent State      
class AgentState(TypedDict):
    """Speichert den aktuellen Zustand des Agenten"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    attempts: int
    next: Literal["improve_message", "generate_changelog"]
    analysis: Optional[GitDiffAnalysis]  # Speichert die GitDiffAnalysis
    final_message: Optional[str]  # Speichert die finale Commit Message
    message_history: List[Dict[str, Any]]  # Speichert alle Message-Versuche

######################################################################################################
class OllamaWrapper:
    """Wrapper für Ollama API Calls"""
    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.temperature = 0

    def _chat_with_format(self, prompt: str, vars: dict, format_schema=None) -> dict:
        """Helper für formatierten Chat"""
        formatted_prompt = prompt.format(**vars)
        response = ollama.chat(
            model=self.model,
            messages=[{
                'role': 'user',
                'content': formatted_prompt
            }],
            format=format_schema,
            options={
                'temperature': self.temperature
            }
        )
        
        return response

######################################################################################################
# First Node: Get Git Diff

def get_git_diff(state: AgentState) -> AgentState:
    """Git Diff holen"""
    try:
        git = GitHandler()
        diff = git.get_staged_diff()
        state["messages"].append(
            HumanMessage(content=f"Here are the staged changes:\n\n{diff}")
        )
        return state
    except GitHandlerError as e:
        state["messages"].append(
            AIMessage(content=f"Error getting git diff: {str(e)}")
        )
        return state

######################################################################################################
# Second Node: Analyze Changes
# 1. Parst Git Diff
# 2. Für jede Datei:
#    - Extrahiert Diff
#    - Analysiert Purpose
# 3. Erstellt Gesamtanalyse

def parse_git_diff(diff_text: str) -> List[GitFileChange]:
    """
    Parst Git Diffs mit unidiff Library
    Siehe: https://github.com/matiasb/python-unidiff
    """
    patch_set = PatchSet(StringIO(diff_text))
    changes: List[GitFileChange] = []
    
    print(f"Found {len(patch_set)} files in diff")
    
    for patched_file in patch_set:
        # Basis-Informationen
        path = patched_file.path.lstrip('b/')  # Entferne 'b/' Prefix
        
        # Change Type Detection
        if patched_file.is_added_file:  # Neue Datei
            change_type = "NEW"
            old_path = None
            print(f"NEW file: {path}")
        elif patched_file.is_removed_file:  # Gelöschte Datei
            change_type = "DELETED"
            old_path = patched_file.source_file.lstrip('a/')
            print(f"DELETED file: {path}")
        elif patched_file.is_rename:  # Umbenannte Datei
            change_type = "RENAMED"
            old_path = patched_file.source_file.lstrip('a/')
            print(f"RENAMED file from {old_path} to {path}")
        elif patched_file.is_binary_file:  # Binärdatei
            change_type = "BINARY"
            old_path = None
            print(f"BINARY file: {path}")
        else:  # Normale Änderung
            change_type = "MODIFIED"
            old_path = None
            print(f"MODIFIED file: {path}")
            
        # Hunk Analysis
        hunks = []
        total_added = 0
        total_removed = 0
        
        for hunk in patched_file:
            added = len([l for l in hunk if l.is_added])
            removed = len([l for l in hunk if l.is_removed])
            total_added += added
            total_removed += removed
            
            hunk_info = {
                "old_start": hunk.source_start,
                "old_length": hunk.source_length,
                "new_start": hunk.target_start,
                "new_length": hunk.target_length,
                "added_lines": added,
                "removed_lines": removed,
                "modified_lines": len(hunk)
            }
            hunks.append(hunk_info)
            
        print(f"  Lines: +{total_added} -{total_removed}")
            
        # Erstelle direkt ein GitFileChange-Objekt
        change = GitFileChange(
            path=path,
            change_type=change_type,
            old_path=old_path,
            added_lines=total_added,
            removed_lines=total_removed,
            hunks=hunks,
            purpose=""  # Wird später vom LLM gefüllt
        )
        changes.append(change)  # Füge das Objekt direkt hinzu
    
    return changes

def extract_file_diff(full_diff: str, file_path: str) -> str:
    """Extrahiert den Diff für eine spezifische Datei"""
    lines = full_diff.split('\n')
    file_diff = []
    in_target_file = False
    
    for line in lines:
        if line.startswith('diff --git') and file_path in line:
            in_target_file = True
        elif line.startswith('diff --git') and in_target_file:
            break
        
        if in_target_file:
            file_diff.append(line)
            
    return '\n'.join(file_diff)

def debug_print(title: str, content: Any, style: str = "blue"):
    """Formatierte Debug-Ausgabe"""
    console.print(f"\n[bold {style}]{title}[/bold {style}]")
    
    if isinstance(content, (dict, str)) and isinstance(content, str) and content.startswith("{"):
        # JSON formatieren
        try:
            if isinstance(content, str):
                content = json.loads(content)
            console.print(Panel(Syntax(json.dumps(content, indent=2), "json", theme="monokai")))
        except:
            console.print(Panel(str(content)))
    else:
        console.print(Panel(str(content)))

def analyze_changes(state: AgentState) -> AgentState:
    """Änderungen analysieren"""
    ollama_client = OllamaWrapper()
    
    last_message = state["messages"][-1].content
    parsed_changes = parse_git_diff(last_message)
    
    analyzed_files: List[GitFileChange] = []
    for file_change in parsed_changes:
        debug_print(f"Processing File", file_change.path, "cyan")
        
        file_prompt = """Act as an expert software engineer. Analyze this specific file change and provide a purpose description:
        
        File: {path}
        Type: {change_type}
        Lines: +{added} -{removed}
        
        Content from diff:
        {diff}
        
        Provide a concise, technical purpose description that explains:
        1. What exactly changed in this file
        2. Why this change was made (based on code context)
        3. How it fits into the overall changes
        4. IMPORTANT: Use senior technical descriptions
        
        Return your response as a JSON object with a 'purpose' field."""  # Klarere Anweisung
        
        file_diff = extract_file_diff(last_message, file_change.path)
        debug_print("File Diff", file_diff, "yellow")
        
        response = ollama_client._chat_with_format(
            prompt=file_prompt,
            vars={
                "path": file_change.path,
                "change_type": file_change.change_type,
                "added": file_change.added_lines,
                "removed": file_change.removed_lines,
                "diff": file_diff
            },
            format_schema={"type": "object", "properties": {"purpose": {"type": "string"}}}
        )
        
        debug_print("LLM Response", response, "green")
        debug_print("Purpose", response['message']['content'], "magenta")
        
        try:
            purpose = json.loads(response['message']['content'])['purpose']
            debug_print("Extracted purpose", purpose, "green")  # Debug 5
            
            analyzed_file = GitFileChange(
                path=file_change.path,
                change_type=file_change.change_type,
                old_path=file_change.old_path,
                added_lines=file_change.added_lines,
                removed_lines=file_change.removed_lines,
                hunks=file_change.hunks,
                purpose=purpose
            )
            analyzed_files.append(analyzed_file)
            
        except Exception as e:
            debug_print(f"Error processing file {file_change.path}", str(e), "red")  # Debug 6
            # Fallback
            analyzed_file = GitFileChange(
                path=file_change.path,
                change_type=file_change.change_type,
                old_path=file_change.old_path,
                added_lines=file_change.added_lines,
                removed_lines=file_change.removed_lines,
                hunks=file_change.hunks,
                purpose=f"Changes in {file_change.path}"  # Fallback purpose
            )
            analyzed_files.append(analyzed_file)
    
    # Dann die Gesamtanalyse
    summary_prompt = """Act as an expert software engineer. Analyze these parsed git changes and provide a technical-level summary:

    Changes Overview:
    {changes_overview}
    
    Detailed File Purposes:
    {purposes}
    
    Based on these changes:
    1. Write a brief technical summary (2-3 sentences)
    2. Determine the primary change type (feat/fix/docs/refactor/test/chore/style/perf)
    3. IMPORTANT: Are there any breaking changes? If yes, explain why.
    
    Consider:
    - The overall pattern of changes
    - The relationships between changed files
    - The technical implications
    - The primary purpose of these changes
    - Breaking changes (API changes, schema changes, etc.)"""
    
    # Erstelle übersichtliche Zusammenfassungen
    changes_overview = "\n".join([
        f"- {f.path}: {f.change_type} (+{f.added_lines}/-{f.removed_lines} lines)"
        for f in analyzed_files
    ])
    
    purposes = "\n".join([
        f"- {f.path}: {f.purpose}"
        for f in analyzed_files
    ])
    
    response = ollama_client._chat_with_format(
        prompt=summary_prompt,
        vars={
            "changes_overview": changes_overview,
            "purposes": purposes
        },
        format_schema=GitDiffAnalysis.model_json_schema()
    )

    # Erstelle die finale Analyse
    response_data = json.loads(response['message']['content'])
    analysis = GitDiffAnalysis(
        summary=response_data['summary'],
        change_type=response_data['change_type'],
        files=analyzed_files,
        breaking_change=response_data['breaking_change'],
    )
    
    # Debug: Zeige komplette Analyse
    debug_print("Complete GitDiffAnalysis", analysis.model_dump_json(indent=2), "yellow")
    
    # Speichere die Analyse im State
    state["analysis"] = analysis
    
    state["messages"].append(
        AIMessage(content=analysis.model_dump_json(indent=2))
    )
    
    return state

######################################################################################################
# Third Node: Generate Commit Message
def generate_commit_message(state: AgentState) -> AgentState:
    """
    Node 3: Generiert eine Conventional Commit Message
    - Nutzt die GitDiffAnalysis
    - Folgt dem Format: type(scope): description
    - Berücksichtigt Breaking Changes
    """
    ollama_client = OllamaWrapper()
    
    # Hole die vorherige Analyse
    analysis = json.loads(state["messages"][-1].content)
    
    # Extrahiere mögliche Scopes aus Dateipfaden
    file_paths = [f['path'] for f in analysis['files']]
    common_dirs = set()
    for path in file_paths:
        parts = path.split('/')
        if len(parts) > 1:
            common_dirs.add(parts[1])  # Nimm den ersten Ordner
    
    prompt = """Act as an expert software engineer. Generate a concise Conventional Commit message:

    {analysis}

    Note: This change is{breaking_note} a breaking change.
    Detected possible scopes from paths: {scopes}

    STRICT COMMIT RULES:
    1. Format: <type>(<scope>): <imperative-verb> <what-and-why>
       - If breaking change: <type>(<scope>)!: <description>
       - Scope should be: {scopes}
       - MUST be under 50 characters total
    
    2. Types: feat|fix|docs|refactor|test|chore|style|perf
    
    3. Description MUST:
       - START with IMPERATIVE verb (add/implement/update/fix)
       - Don't capitalize the first letter
       - Be specific about WHAT is being changed
       - Be under 50 characters
       - Not end with period
       - Use imperative mood (NO: added/implemented/fixed)
    
    Return a JSON object following the ConventionalCommit schema."""

    response = ollama_client._chat_with_format(
        prompt=prompt,
        vars={
            "analysis": json.dumps(analysis, indent=2),
            "breaking_note": "" if analysis['breaking_change'] else " NOT",
            "scopes": ", ".join(sorted(common_dirs)) or "none detected"
        },
        format_schema=ConventionalCommit.model_json_schema()
    )

    # Parse die Response
    commit_data = json.loads(response['message']['content'])
    
    # Stelle sicher, dass breaking aus der Analyse übernommen wird
    commit_data['breaking'] = analysis['breaking_change']
    
    commit = ConventionalCommit(**commit_data)
    
    # Formatiere die Commit Message
    message = f"{commit.type}"
    if commit.scope:
        message += f"({commit.scope})"
    if commit.breaking:
        message += "!"
    message += f": {commit.description}"
    
    if commit.body:
        message += f"\n\n{commit.body}"
    if commit.footer:
        message += f"\n\n{commit.footer}"
    
    debug_print("Generated Commit Message", message, "green")
    
    state["messages"].append(
        AIMessage(content=message)
    )
    
    return state

######################################################################################################
# Fourth Node: Check Quality
def check_quality(state: AgentState) -> AgentState:
    """Node 4: Simple Binary Quality Check"""
    ollama_client = OllamaWrapper()
    message = state["messages"][-1].content
    
    prompt = """Act as a Conventional Commits expert. Check if this commit message is valid:

    Commit Message: {message}

    VALIDATION RULES:
    1. Format must be: <type>[optional_scope]: <description>
       - type: feat|fix|docs|refactor|test|chore|style|perf
       - scope: OPTIONAL, in parentheses
       - description: imperative, max 80 chars
       - first letter must be lowercase
    
    2. Breaking changes:
       - Add ! before : for breaking changes
       
    3. Common issues:
       - Wrong type
       - Past tense used
       - Too long (>200 chars)
       - Non-imperative mood
       - Capitalized first letter
       
       Give a binary score true or false score to indicate whether the commit message is valid or not.
       Don't be very strict."""

    response = ollama_client._chat_with_format(
        prompt=prompt,
        vars={"message": message},
        format_schema={
            "type": "object",
            "properties": {
                "is_valid": {"type": "boolean"}
            },
            "required": ["is_valid"]
        }
    )

    quality = CommitQuality(**json.loads(response['message']['content']))
    debug_print("Quality Check", quality.model_dump(), "yellow")
    
    # Speichere Quality Check im State
    state["messages"].append(
        AIMessage(content=json.dumps(quality.model_dump()))
    )
    
    # Speichere den Quality Check in der History
    if "message_history" not in state:
        state["message_history"] = []
        
    state["message_history"].append({
        "attempt": state["attempts"],
        "message": message,
        "quality_check": quality.model_dump(),
        "status": "success" if quality.is_valid else "failed"
    })
    
    # Entscheidungslogik
    if quality.is_valid or state["attempts"] >= 5:
        state["final_message"] = message
        state["next"] = "generate_changelog"
        
        # Speichere finalen Status
        state["message_history"].append({
            "attempt": state["attempts"],
            "message": message,
            "status": "final",
            "reason": "valid" if quality.is_valid else "max_attempts_reached"
        })
    else:
        state["attempts"] += 1
        state["next"] = "improve_message"
    
    return state

def improve_message(state: AgentState) -> AgentState:
    """Node 5: Verbessert die Commit Message"""
    ollama_client = OllamaWrapper()
    
    # Die letzte Message ist der Quality Check, die vorletzte ist die Commit Message
    messages = state["messages"]
    commit_message = messages[-2].content
    quality_check = json.loads(messages[-1].content)
    
    # Speichere den fehlgeschlagenen Versuch
    if "message_history" not in state:
        state["message_history"] = []
        
    state["message_history"].append({
        "attempt": state["attempts"],
        "message": commit_message,
        "quality_check": quality_check,
        "status": "failed"
    })
    
    prompt = """Act as an expert software engineer. Fix this commit message:

    Original Message: {message}

    STRICT RULES:
    1. Format: <type>(<scope>): <description>
    2. Must use imperative mood (add/fix/update)
    3. scope: OPTIONAL, in parentheses
    4. Must be under 50 chars
    5. Must be specific and technical
    6. ONLY first letter must be lowercase
    7. NO duplicate information in scope/description
    
    Return ONLY the final commit message as plain text."""

    response = ollama.chat(
        model=ollama_client.model,
        messages=[{
            'role': 'user',
            'content': prompt.format(message=commit_message)
        }],
        options={'temperature': 0}
    )

    message = response['message']['content'].strip()
    debug_print("Improved Message", message, "cyan")
    
    # Speichere den verbesserten Versuch
    state["message_history"].append({
        "attempt": state["attempts"],
        "message": message,
        "status": "improved"
    })
    
    state["messages"].append(
        AIMessage(content=message)
    )
    
    state["next"] = "check_quality"
    return state

######################################################################################################
# Fifth Node: Generate Changelog
def generate_changelog(state: AgentState) -> AgentState:
    """
    Node 6: Generiert einen schönen Changelog Eintrag
    - Formatiert als Markdown
    - Speichert in CHANGELOG_AGENT.md
    - Zeigt Preview mit Rich
    """
    analysis = state["analysis"]  # GitDiffAnalysis Objekt
    commit_message = state["final_message"]
    
    # Erstelle schönen Changelog Eintrag
    changelog_entry = f"""## {commit_message}

### 🔍 Summary
{analysis.summary}

### 📝 Changed Files
{chr(10).join([f"- **{f.path}**: {f.purpose}" for f in analysis.files])}

### 🔄 Type: `{analysis.change_type}`
{"### ⚠️ BREAKING CHANGES" if analysis.breaking_change else ""}
"""
    
    # Speichere in CHANGELOG.md
    with open("CHANGELOG_AGENT.md", "a") as f:
        f.write(f"\n{changelog_entry}\n")
    
    # Zeige Preview mit Rich
    console.print("\n[bold blue]📋 Generated Changelog Entry:[/bold blue]")
    console.print(Panel(
        Syntax(changelog_entry, "markdown", theme="monokai"),
        title="[bold green]Preview",
        border_style="green"
    ))
    
    state["messages"].append(
        AIMessage(content=changelog_entry)
    )
    
    return state

######################################################################################################
# Der Hauptagent, der alles steuert
class CommitAgent:
    """
    Der Chef-Agent, der den ganzen Workflow koordiniert
    - Erstellt den Graphen (Workflow)
    - Führt die Schritte aus
    """
    def __init__(self):
        self.graph = create_graph()
        self.app = self.graph.compile()
        
        # Erstelle Visualisierung direkt nach Graph-Erstellung
        viz_dir = Path("viz")
        viz_dir.mkdir(exist_ok=True)
    
    def visualize_workflow(self, save_path="viz/workflow.png"):
        """Speichert den Workflow als PNG"""
        try:
            # Nutze MermaidDrawMethod.API für die Visualisierung
            png_data = self.app.get_graph().draw_mermaid_png(
                draw_method=MermaidDrawMethod.API
            )
            with open(save_path, 'wb') as f:
                f.write(png_data)
            print(f"Graph gespeichert als: {save_path}")
        except Exception as e:
            print(f"Fehler beim Visualisieren: {e}")
    
    def run(self, messages: List[BaseMessage]) -> AgentState:
        """Startet den Workflow synchron"""
        return self.app.invoke({
            "messages": messages,
            "attempts": 0,
            "next": "get_diff"
        })
    
    def stream(self, messages: List[BaseMessage]):
        """
        Streamt den Workflow-Fortschritt für die CLI
        - Zeigt jeden Schritt des Workflows an
        - Erlaubt uns den Fortschritt zu verfolgen
        """
        # Erstelle den initialen State mit allen erforderlichen Feldern
        initial_state = {
            "messages": messages if messages else [],
            "attempts": 0,
            "next": "generate_message",
            "analysis": None,  # Initialisiere analysis
            "final_message": None,  # Initialisiere final_message
            "message_history": []  # Initialisiere message_history
        }
        # Nutze invoke statt stream für den ersten Test
        return [self.app.invoke(initial_state)]

# GRAPH (Workflow) Setup
def create_graph():
    """
    Baut unseren Workflow zusammen
    - Definiert die Reihenfolge der Arbeitsschritte
    - Verbindet die Nodes mit Edges (wie eine Straßenkarte)
    """
    workflow = StateGraph(AgentState)
    
    # Nodes
    workflow.add_node("get_diff", get_git_diff)
    workflow.add_node("analyze", analyze_changes)
    workflow.add_node("generate_message", generate_commit_message)
    workflow.add_node("check_quality", check_quality)
    workflow.add_node("improve_message", improve_message)
    workflow.add_node("generate_changelog", generate_changelog)
    
    # Basis-Flow
    workflow.add_edge(START, "get_diff")
    workflow.add_edge("get_diff", "analyze")
    workflow.add_edge("analyze", "generate_message")
    workflow.add_edge("generate_message", "check_quality")
    
    # Verzweigungen basierend auf State
    workflow.add_conditional_edges(
        "check_quality",
        lambda x: x["next"],
        {
            "improve_message": "improve_message",
            "generate_changelog": "generate_changelog"
        }
    )
    workflow.add_edge("improve_message", "check_quality")  # Direkter Weg zurück zur Qualitätsprüfung
    workflow.add_edge("generate_changelog", END)
    
    return workflow

# Eine globale Instanz unseres Graphen erstellen
#graph = create_graph()
