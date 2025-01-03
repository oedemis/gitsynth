from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Dict, Any, Literal
from rich.console import Console
from ..utils import console
import json

COMMIT_TYPES = {
    "feat": {
        "description": "New Feature",
        "priority": 1,
        "examples": [
            "Add editor component",
            "Implement helper utils",
            "Create new API endpoint"
        ]
    },
    "fix": {
        "description": "Bug Fix", 
        "priority": 2,
        "examples": [
            "Fix login validation",
            "Resolve memory leak",
            "Fix broken links"
        ]
    },
    "docs": {
        "description": "Documentation",
        "priority": 3,
        "examples": [
            "Update API docs",
            "Add setup guide",
            "Improve README"
        ]
    },
    "refactor": {
        "description": "Code Improvement",
        "priority": 4,
        "examples": [
            "Restructure components",
            "Simplify logic",
            "Move utils to separate file"
        ]
    },
    "test": {
        "description": "Test Changes",
        "priority": 4,
        "examples": [
            "Add unit tests",
            "Update test fixtures",
            "Fix flaky tests"
        ]
    }
}

class FileChange(BaseModel):
    """Schema für Änderungen in einer Datei"""
    file_path: str = Field(description="Pfad zur geänderten Datei")
    is_new: bool = Field(description="Ist dies eine neue Datei?")
    changes: str = Field(description="Konkrete Änderungen in der Datei")
    context: str = Field(description="Technischer Kontext der Änderung")

class DiffAnalysis(BaseModel):
    """Schema für die Git Diff Analyse"""
    files: list[FileChange] = Field(description="Liste aller geänderten Dateien")
    main_change: str = Field(description="Wichtigste Änderung im Diff")
    relationships: str = Field(description="Zusammenhänge zwischen den Dateien")
    impact: str = Field(description="Mögliche Auswirkungen der Änderungen")

class CommitAnalysis(BaseModel):
    """Schema for Git Commit Analysis"""
    commit_type: Literal["feat", "fix", "docs", "refactor", "test"] = Field(
        description="The commit type based on the type of change:"
        + "\n".join([f"\n- {k}: {v['description']} (Priority: {v['priority']})" 
                    for k,v in COMMIT_TYPES.items()])
    )
    short_message: str = Field(
        description="""Short, concise commit message:
        - Start with imperative verb in English (Add/Update/Fix)
        - Max 50 characters
        - Describe main change
        - For multiple files: Most important change first
        
        Examples:
        - feat: Add editor component and helper utils
        - docs: Update API documentation
        - fix: Resolve login validation
        """,
        default=""
    )

class LLMHandlerError(Exception):
    """Basisklasse für LLMHandler Fehler"""
    pass

class LLMHandler:
    """
    LLMHandler verwaltet die KI-Komponenten von GitSynth:
    - ChatOllama: Für die Textgenerierung und Analyse
    - HuggingFace Embeddings: Für die Vektorisierung von Text
    """
    def __init__(self):
        try:
            # 1. Base Model Setup
            self.base_model = ChatOllama(
                model="llama3.2",
                temperature=0.0,
                timeout=30,
            )
            
            # 2. Structured Output Models
            self.analysis_model = self.base_model.with_structured_output(DiffAnalysis)
            self.commit_model = self.base_model.with_structured_output(CommitAnalysis)
            
            # 3. Prompts in Processing Order
            # 3.1 Raw Analysis (Technical Details)
            self.raw_analysis_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a Git expert analyzing code changes. Provide a detailed technical analysis of this diff.

                Required Analysis Points:
                1. File Changes (MOST IMPORTANT):
                   - List ALL modified files
                   - Explain ALL technical changes in detail
                   - Include ALL code additions and modifications
                   - Note ALL new features and configurations

                2. Technical Impact:
                   - Describe the purpose of EACH change
                   - Explain ALL implementation details
                   - Note ALL configuration changes
                   - Identify ALL performance impacts

                3. Dependencies & Relationships:
                   - How do ALL changes interact?
                   - What components are affected?
                   - List ALL new configurations
                   - Impact on existing functionality

                4. Technical Context:
                   - Purpose of EACH new feature
                   - Problems being solved
                   - Performance implications
                   - Future capabilities

                CRITICAL: Include EVERY change shown in the diff, no matter how small.
                Format your analysis with clear sections and technical details.
                """),
                ("human", "{diff}")
            ])
            
            # 3.2 Structured Analysis (JSON Format)
            self.analyze_changes_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a Git expert. Your task is to convert the provided technical analysis into a structured output that EXACTLY matches this schema:

                DiffAnalysis Schema:
                {{
                    "files": [
                        {{
                            "file_path": str,  # EXACT path from diff
                            "is_new": bool,    # true for "new file mode" in diff
                            "changes": str,    # Technical changes in detail
                            "context": str     # Technical purpose
                        }}
                    ],
                    "main_change": str,      # Most significant change
                    "relationships": str,    # How changes interact
                    "impact": str           # Technical implications
                }}

                CRITICAL RULES:
                1. Use EXACT file paths from the diff
                2. Set is_new=true for "new file mode" entries
                3. Be specific about changes in each file
                4. Focus on technical implications
                """),
                ("human", "Based on this technical analysis, create a structured output:\n\n{analysis}")
            ])
            
            # 3.3 Commit Analysis (Message Generation)
            examples_text = "\n".join([f"- {k}: {example}" 
                                     for k,v in COMMIT_TYPES.items() 
                                     for example in v["examples"]])
            categories_text = "\n".join([f'- {k}: {v["description"]} (Priorität: {v["priority"]})' 
                                       for k,v in COMMIT_TYPES.items()])
             
            self.determine_type_prompt = ChatPromptTemplate.from_messages([
                ("system", f"""Act as an Git Expert. Based on the analysis, determine the most appropriate commit type and create a concise message.
                
                Important rules for categorization (by priority):
                {categories_text}
                
                Examples of good messages:
                {examples_text}
                
                Rules for the message:
                1. Short and concise (max 50 characters)
                2. Start with imperative verb in English (Add/Update/Fix)
                3. Describe main change
                4. Always write messages in English
                """),
                ("human", "Based on this Git Diff Analysis, create a commit message:\n{analysis}")
            ])
            
            # 4. Chain Setup
            # 4.1 Individual Chains
            self.raw_chain = self.raw_analysis_prompt | self.base_model
            self.structured_chain = self.analyze_changes_prompt | self.analysis_model
            self.commit_chain = self.determine_type_prompt | self.commit_model
            
            # 4.2 Combined Analysis Chain
            # Chain Flow:
            # 1. Input diff -> Raw Analysis (Technical Details)
            # 2. Raw Analysis -> Structured Analysis (Pydantic Model)
            # 3. Structured Analysis -> Commit Analysis (Message)
            self.full_chain = (
                # 1. Raw Analysis
                {"diff": lambda x: x}  # Input: Git Diff
                | self.raw_chain      # Output: {"content": str}
                | {"analysis": lambda x: x.content}  # ✅ Key für Structured Analysis
                
                # 2. Structured Analysis
                | self.structured_chain  # Output: DiffAnalysis
                | {"analysis": lambda x: x}  # ✅ Pydantic Model für Commit Analysis
                
                # 3. Commit Analysis
                | self.commit_chain  # Output: CommitAnalysis
            )
            
            # 5. Additional Components
            self.embeddings = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-en-v1.5",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            
        except Exception as e:
            console.print(f"[red]Fehler bei der Initialisierung des LLMHandler: {str(e)}[/red]")
            raise LLMHandlerError(f"Konnte LLMHandler nicht initialisieren: {str(e)}")
    
    def analyze_diff(self, diff_text: str) -> Dict[str, Any]:
        """Analysiert Git Diff mit zweistufiger Analyse"""
        try:
            # 1. Raw Analysis
            console.print("[yellow]1. Erstelle technische Analyse...[/yellow]")
            raw_analysis = self.raw_chain.invoke({"diff": diff_text})
            console.print("[green]✓ Technische Analyse erstellt[/green]")
            
            # 2. Structured Analysis
            console.print("[yellow]2. Strukturiere Analyse...[/yellow]")
            diff_analysis = self.structured_chain.invoke({"analysis": raw_analysis.content})
            console.print("[green]✓ Analyse strukturiert[/green]")
            
            # 3. Commit Analysis
            console.print("[yellow]3. Generiere Commit-Info...[/yellow]")
            final_result = self.commit_chain.invoke({"analysis": diff_analysis})
            console.print("[green]✓ Commit-Info generiert[/green]")
            
            return {
                "commit_type": final_result.commit_type,
                "analysis": diff_analysis,
                "short_message": final_result.short_message,
                "raw_analysis": raw_analysis.content  # Optional: Raw-Analyse für Debug
            }
        except Exception as e:
            console.print(f"[red]Fehler bei der Analyse: {str(e)}[/red]")
            empty_analysis = DiffAnalysis(
                files=[],
                main_change="Fehler bei der Analyse",
                relationships="",
                impact=""
            )
            return {
                "commit_type": "fix",
                "analysis": empty_analysis,
                "short_message": "Fix analysis error",
                "raw_analysis": str(e)
            }
    
    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Erstellt Embeddings für die gegebenen Texte
        
        Args:
            texts: Liste von Texten
            
        Returns:
            Liste von Embedding-Vektoren
        """
        return self.embeddings.embed_documents(texts)
    
    def debug_llm_output(self, diff_text: str) -> Dict[str, str]:
        """Debug-Methode um das rohe LLM-Output zu analysieren"""
        try:
            # 1. Raw Analysis
            raw_result = self.raw_chain.invoke({"diff": diff_text})
            
            # 2. Structured Analysis
            try:
                structured_result = self.structured_chain.invoke({
                    "analysis": raw_result.content
                })
                
                # 3. Commit Analysis
                commit_result = self.commit_chain.invoke({
                    "analysis": structured_result
                })
                
                return {
                    "raw_output": raw_result.content,
                    "structured_output": structured_result.model_dump_json(indent=2) if structured_result else "No structured output",
                    "commit_output": commit_result.model_dump_json(indent=2) if commit_result else "No commit output"
                }
                
            except Exception as e:
                return {
                    "raw_output": raw_result.content,
                    "structured_output": f"Failed to structure: {str(e)}",
                    "commit_output": "No commit output"
                }
                
        except Exception as e:
            return {
                "raw_output": f"Failed: {str(e)}",
                "structured_output": None,
                "commit_output": None
            }