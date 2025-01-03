import ollama
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Literal, List, Optional
from ..utils import console
from rich.panel import Panel
from rich.syntax import Syntax
import re
import os
from langsmith import traceable
from langsmith import Client
from dotenv import load_dotenv

# Models für Structured Output
class FileChange(BaseModel):
    file_path: str = Field(description="Full path to the changed file")
    change_type: Literal["new", "deleted", "modified", "renamed", "mode_changed"] = Field(
        description="Type of change to the file"
    )
    old_path: Optional[str] = Field(
        description="Original path if file was renamed",
        default=None
    )
    changes: str = Field(
        description="Technical description of changes and their purpose",
        max_length=150
    )

class DiffAnalysis(BaseModel):
    """Schema for Git Diff Analysis"""
    files: List[FileChange] = Field(
        description="List of ALL modified files from the diff",
        min_items=1
    )
    main_change: str = Field(
        description="Main technical change across all files",
        max_length=120
    )
    relationships: str = Field(
        description="How ALL files interact with each other",
        max_length=200
    )
    impact: str = Field(
        description="Overall technical impact of ALL changes",
        max_length=150
    )
    commit_type: Literal["feat", "fix", "docs", "refactor", "test", "chore", "style", "perf"] = Field(
        description="Type of commit based on changes"
    )
    commit_message: str = Field(
        description="Short, technical and informative commit message (max 80 chars)",
        max_length=72
    )


class OllamaHandlerError(Exception):
    """Base class for OllamaHandler errors"""
    pass
    

class OllamaHandler:
    """Handler für Ollama mit Structured Output Support"""
    
    # Verbesserte Prompts
    ANALYSIS_PROMPT = """You are a Git expert analyzing git diffs. Provide a detailed technical analysis of this git diff.

    CRITICAL RULES:
        1. Git Diff Pattern Detection for EACH file (MOST IMPORTANT):
        - Parse diff headers carefully for EACH file:
            * new file: "new file mode" -> NEW file
            * deleted: "deleted file mode" -> DELETED file
            * renamed: "rename from X to Y" -> RENAMED FILE NAME (store old path)
            * mode change: "mode change" -> MODE_CHANGED file
            * modified: file content changes without above -> MODIFIED file
            * Binary file -> handle as BINARY
            * Submodule changes -> detect SUBMODULE updates
            * Merge conflicts -> detect CONFLICT markers

        2. Technical Analysis Requirements:
            - Analyze EACH file's changes in detail
            - Explain technical purpose of changes
            - Identify code patterns and improvements
            - Detect breaking changes

        3. Relationships & Impact:
            - How do files interact?
            - Which components are affected?
            - What is the main technical change?
            - Impact on existing functionality
            
        4. Main Change & Impact:
            - Summarize the core technical change
            - Focus on the system being built
            - Be specific about technical capabilities
            - How ALL files interact with each other
            - Overall technical impact of changes
        
    IMPORTANT:
        - Include EVERY change shown in the diff
        - Format with clear section headers        
        - ALL sections above MUST be present

    ## Git Diff:
    {diff}
    """
    ##- FORMAT: "<verb in present tense> <technical-components> with <specific-functions>"
    STRUCTURED_PROMPT = """You are an Git expert. Your task is to convert the provided technical Analysis into a structured output:
                
        ## Here is the technical Analysis:
        {analysis}
        
        1. COMMIT MESSAGE RULES (MOST CRITICAL):
            - START your commit message always with IMPERATIVE VERB (Add/Fix/Refactor)
            - Be concise (under 80 chars)
            - Focus on the MAIN technical capability being added
            - Include the PRIMARY technical component
            - Explain the SPECIFIC technical function/purpose
            - AVOID buzzwords or vague terms or general sentences
            - Use INSPIRING clear language from the analysis and rewrite it if its needed
            
        2. Commit Type Selection (in order of priority):
            feat:     (HIGHEST) New feature/capability
            fix:      Bug fix/error correction  
            docs:     Documentation only
            refactor: Code restructuring that neither fixes a bug nor adds a feature
            test:     Adding/fixing tests
            chore:    Build process, auxiliary tools, other changes that don't modify src or test files
            perf:     A code change that improves performance
            style:    (LOWEST) Formatting, missing semicolons, no code change
        
        3. IMPORTANT:
            - Multiple files need clear main change
            - Avoid redundant descriptions
            - If ANY new feature exists -> Commit Type: feat
            - If NO new features but has fixes -> Commit Type: fix
            - If ONLY performance improvements -> Commit Type: perf
            - If ONLY code restructuring -> Commit Type: refactor
            - Otherwise, use the highest priority type that matches
        """
    

    def __init__(self):
        # .env Datei laden
        load_dotenv()
        
        self.model = "llama3.2"
        self.temperature = 0.0
        
        # LangSmith Client initialisieren
        self.langsmith_client = Client()
        
        # Sicherstellen dass die Umgebungsvariablen gesetzt sind
        if not os.getenv("LANGCHAIN_API_KEY"):
            console.print("[yellow]Warning: LANGCHAIN_API_KEY nicht gesetzt - LangSmith Tracing deaktiviert[/yellow]")
        if not os.getenv("LANGCHAIN_TRACING_V2"):
            os.environ["LANGCHAIN_TRACING_V2"] = "true"

    @traceable(name="chat_with_format") # Tracing für diese Methode aktivieren
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
        
    @traceable(name="analyze_diff") # Tracing für diese Methode aktivieren  
    def analyze_diff(self, diff_text: str) -> Dict[str, Any]:
        try:
            # 1. Raw Analysis
            console.print("[yellow]1. Creating technical analysis...[/yellow]")
            raw_response = self._chat_with_format(
                self.ANALYSIS_PROMPT, 
                {"diff": diff_text}
            )
            
            # 2. Structured Analysis
            console.print("[yellow]2. Structuring analysis...[/yellow]")
            diff_response = self._chat_with_format(
                self.STRUCTURED_PROMPT,
                {"analysis": raw_response['message']['content']},
                format_schema=DiffAnalysis.model_json_schema()
            )
            
            # 3. Commit Analysis
            console.print("[yellow]3. Generating commit info...[/yellow]")
            diff_analysis = DiffAnalysis.model_validate_json(diff_response['message']['content'])
            
            return {
                "commit_type": diff_analysis.commit_type,
                "analysis": diff_analysis,
                "commit_message": diff_analysis.commit_message,
                "raw_analysis": raw_response['message']['content']
            }
            
        except Exception as e:
            console.print(f"[red]Error during analysis: {str(e)}[/red]")
            return self._create_error_response(str(e))

    @traceable(name="debug_llm_output") # Tracing für diese Methode aktivieren
    def debug_llm_output(self, diff_text: str) -> Dict[str, str]:
        try:
            # 1. Input Diff
            console.print("\n[bold blue]Input Diff:[/bold blue]")
            console.print(Panel(
                Syntax(diff_text, "diff", theme="monokai", line_numbers=True),
                title="[bold]Complete Git Diff[/bold]",
                border_style="blue"
            ))

            # 2. Technical Analysis
            raw_response = self._chat_with_format(
                self.ANALYSIS_PROMPT, 
                {"diff": diff_text}
            )
            
            # 3. Structured Analysis
            diff_response = self._chat_with_format(
                self.STRUCTURED_PROMPT,
                {"analysis": raw_response['message']['content']},
                format_schema=DiffAnalysis.model_json_schema()
            )
            
            diff_analysis = DiffAnalysis.model_validate_json(diff_response['message']['content'])

            # Return für CLI-Format
            return {
                "raw_output": raw_response['message']['content'],
                "structured_output": diff_analysis.model_dump_json(indent=2),
            }

        except Exception as e:
            console.print(f"[red]Error during debug: {str(e)}[/red]")
            return {
                "raw_output": f"Failed: {str(e)}",
                "structured_output": None,
                "commit_validation": None
            }

    def _create_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Creates error response with empty analysis"""
        empty_analysis = DiffAnalysis(
            files=[FileChange(
                file_path="error.txt",
                change_type="modified",
                changes="Analysis failed",
                old_path=None
            )],
            main_change="Analysis failed",
            relationships="",
            impact="",
            commit_type="fix",
            commit_message="Fix analysis error"
        )
        return {
            "commit_type": "fix",
            "analysis": empty_analysis,
            "commit_message": "Fix analysis error",
            "raw_analysis": error_msg
        }