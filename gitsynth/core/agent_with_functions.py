"""
GitSynth Commit Agent - Ein intelligenter Helfer für Git Commits
"""

from typing import Annotated, Sequence, List, Optional, Literal, Any, Dict
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field
import json
from .git import GitHandler, GitHandlerError
from unidiff import PatchSet, PatchedFile
from io import StringIO
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

# LLM Setup
llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL", "llama2"),
    temperature=0
)

######################################################################################################
# Pydantic Models
# ... [vorherige Pydantic Models bleiben gleich] ...
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
# Tools für Function Calling

@tool
def analyze_file_purpose(
    path: str, 
    change_type: str, 
    added_lines: int, 
    removed_lines: int, 
    diff: str
) -> str:
    """Analyze a single file change and determine its purpose.
    
    Args:
        path: File path
        change_type: Type of change (NEW, MODIFIED etc)
        added_lines: Number of added lines
        removed_lines: Number of removed lines
        diff: The file's diff content
    
    Returns:
        str: Technical description of the change purpose
    """
    return llm.invoke(
        f"""Analyze this file change:
        Path: {path}
        Type: {change_type}
        Lines: +{added_lines} -{removed_lines}
        
        Diff:
        {diff}
        
        Provide a technical, concise description of what changed and why."""
    ).content

@tool
def analyze_changes_summary(changes: List[Dict]) -> GitDiffAnalysis:
    """Create a summary analysis of all changes.
    
    Args:
        changes: List of file changes with their purposes
    
    Returns:
        GitDiffAnalysis: Complete analysis of changes
    """
    response = llm.invoke(
        f"""Analyze these changes and provide:
        1. Technical summary (2-3 sentences)
        2. Change type (feat/fix/docs/refactor/test/chore/style/perf)
        3. Are there breaking changes?
        
        Changes:
        {json.dumps(changes, indent=2)}""",
        format=GitDiffAnalysis.model_json_schema()
    )
    return GitDiffAnalysis(**json.loads(response.content))

@tool
def generate_commit(analysis: GitDiffAnalysis) -> ConventionalCommit:
    """Generate a Conventional Commit message.
    
    Args:
        analysis: Complete analysis of changes
    
    Returns:
        ConventionalCommit: Structured commit message
    """
    response = llm.invoke(
        f"""Generate a Conventional Commit message:
        
        Analysis: {analysis.model_dump_json()}
        
        Rules:
        1. Format: <type>(<scope>): <description>
        2. Use imperative mood
        3. Max 50 chars
        4. Be specific and technical""",
        format=ConventionalCommit.model_json_schema()
    )
    return ConventionalCommit(**json.loads(response.content))

@tool
def check_commit_quality(message: str) -> CommitQuality:
    """Check if a commit message meets quality standards.
    
    Args:
        message: The commit message to check
    
    Returns:
        CommitQuality: Quality check result
    """
    response = llm.invoke(
        f"""Check if this commit message is valid:
        Message: {message}
        
        Rules:
        1. Correct format
        2. Imperative mood
        3. Under 50 chars
        4. Specific and technical
        
        Return true or false.""",
        format=CommitQuality.model_json_schema()
    )
    return CommitQuality(**json.loads(response.content))

######################################################################################################
# Graph Nodes

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

def analyze_changes(state: AgentState) -> AgentState:
    """Änderungen analysieren mit Tools"""
    last_message = state["messages"][-1].content
    parsed_changes = parse_git_diff(last_message)
    
    # Analysiere jede Datei mit Tool
    for change in parsed_changes:
        change.purpose = analyze_file_purpose(
            path=change.path,
            change_type=change.change_type,
            added_lines=change.added_lines,
            removed_lines=change.removed_lines,
            diff=extract_file_diff(last_message, change.path)
        )
    
    # Erstelle Gesamtanalyse mit Tool
    analysis = analyze_changes_summary([
        {
            "path": c.path,
            "change_type": c.change_type,
            "added_lines": c.added_lines,
            "removed_lines": c.removed_lines,
            "purpose": c.purpose
        }
        for c in parsed_changes
    ])
    
    state["analysis"] = analysis
    state["messages"].append(
        AIMessage(content=analysis.model_dump_json(indent=2))
    )
    
    return state

def generate_commit_message(state: AgentState) -> AgentState:
    """Generiert Commit Message mit Tool"""
    commit = generate_commit(state["analysis"])
    
    message = f"{commit.type}"
    if commit.scope:
        message += f"({commit.scope})"
    if commit.breaking:
        message += "!"
    message += f": {commit.description}"
    
    state["messages"].append(
        AIMessage(content=message)
    )
    
    return state

def check_quality(state: AgentState) -> AgentState:
    """Prüft Qualität mit Tool"""
    message = state["messages"][-1].content
    quality = check_commit_quality(message)
    
    if quality.is_valid or state["attempts"] >= 5:
        state["final_message"] = message
        state["next"] = "generate_changelog"
    else:
        state["attempts"] += 1
        state["next"] = "improve_message"
    
    state["messages"].append(
        AIMessage(content=json.dumps(quality.model_dump()))
    )
    
    return state

def improve_message(state: AgentState) -> AgentState:
    """Verbessert Message mit neuem Versuch"""
    return generate_commit_message(state)

def generate_changelog(state: AgentState) -> AgentState:
    """Generiert Changelog"""
    analysis = state["analysis"]
    message = state["final_message"]
    
    changelog = f"""## {message}

### 🔍 Summary
{analysis.summary}

### 📝 Changed Files
{chr(10).join([f"- **{f.path}**: {f.purpose}" for f in analysis.files])}

### 🔄 Type: `{analysis.change_type}`
{"### ⚠️ BREAKING CHANGES" if analysis.breaking_change else ""}
"""
    
    with open("CHANGELOG_AGENT.md", "a") as f:
        f.write(f"\n{changelog}\n")
    
    console.print("\n[bold blue]📋 Generated Changelog Entry:[/bold blue]")
    console.print(Panel(
        Syntax(changelog, "markdown", theme="monokai"),
        title="[bold green]Preview",
        border_style="green"
    ))
    
    state["messages"].append(
        AIMessage(content=changelog)
    )
    
    return state

######################################################################################################
# Graph Setup

def create_graph() -> StateGraph:
    """Erstellt den Workflow-Graphen"""
    workflow = StateGraph(AgentState)
    
    # Nodes hinzufügen
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
    
    # Bedingte Kanten
    workflow.add_conditional_edges(
        "check_quality",
        lambda x: x["next"],
        {
            "improve_message": "improve_message",
            "generate_changelog": "generate_changelog"
        }
    )
    
    workflow.add_edge("improve_message", "check_quality")
    workflow.add_edge("generate_changelog", END)
    
    return workflow

class CommitAgent:
    """Der Haupt-Agent"""
    def __init__(self):
        self.graph = create_graph()
        self.app = self.graph.compile()
    
    def run(self, messages: List[BaseMessage]) -> AgentState:
        """Führt den Workflow aus"""
        return self.app.invoke({
            "messages": messages,
            "attempts": 0,
            "next": "get_diff",
            "analysis": None,
            "final_message": None,
            "message_history": []
        })
