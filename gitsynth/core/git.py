from git import Repo as GitRepo
from typing import List, Dict, Optional
from pathlib import Path
import logging

class GitHandlerError(Exception):
    """Basisklasse für GitHandler Fehler"""
    pass

class GitHandler:
    """
    GitHandler verwaltet die Git-Operationen von GitSynth:
    - Staged Changes analysieren
    - Commits erstellen
    - Repository Status prüfen
    """
    def __init__(self, repo_path: str = "."):
        try:
            self.repo = GitRepo(repo_path)
            if self.repo.bare:
                raise GitHandlerError("Kann nicht mit einem bare Repository arbeiten")
        except Exception as e:
            logging.error(f"Fehler bei der Initialisierung des GitHandler: {str(e)}")
            raise GitHandlerError(f"Konnte GitHandler nicht initialisieren: {str(e)}")

    def get_staged_diff(self) -> str:
        """
        Holt den Diff der staged Änderungen
        
        Returns:
            str: Git Diff der staged Änderungen
        
        Raises:
            GitHandlerError: Wenn keine Änderungen staged sind
        """
        try:
            diff = self.repo.git.diff("--cached")
            if not diff:
                raise GitHandlerError("Keine Änderungen staged")
            return diff
        except Exception as e:
            logging.error(f"Fehler beim Holen des Diffs: {str(e)}")
            raise GitHandlerError(f"Konnte Diff nicht holen: {str(e)}")

    def create_commit(self, message: str) -> str:
        """
        Erstellt einen Commit mit der gegebenen Nachricht
        
        Args:
            message: Die Commit-Nachricht
            
        Returns:
            str: Die Commit-ID
            
        Raises:
            GitHandlerError: Wenn der Commit nicht erstellt werden konnte
        """
        try:
            commit = self.repo.index.commit(message)
            return str(commit)
        except Exception as e:
            logging.error(f"Fehler beim Erstellen des Commits: {str(e)}")
            raise GitHandlerError(f"Konnte Commit nicht erstellen: {str(e)}") 