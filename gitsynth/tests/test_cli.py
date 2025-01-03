import pytest
import shutil
import os
from typer.testing import CliRunner
from gitsynth.cli import app
from pathlib import Path
from git import Repo
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

# Rich Console für schöne Ausgaben
console = Console()

# CliRunner für Typer-Tests
runner = CliRunner()

def show_test_step(message: str):
    """Zeigt einen Testschritt schön formatiert an"""
    console.print(Panel(f"[bold blue]🔍 {message}"))

def show_command(cmd: str, output: str = None):
    """Zeigt einen Befehl und seine Ausgabe an"""
    console.print(f"[bold yellow]$ {cmd}")
    if output:
        console.print(Syntax(output, "bash", theme="monokai"))

@pytest.fixture
def test_repo(tmp_path):
    """
    Erstellt ein temporäres Git-Repository für Tests
    
    Dies ist eine pytest Fixture - sie wird vor jedem Test ausgeführt
    und erstellt eine frische Testumgebung
    """
    show_test_step("Erstelle Test-Repository")
    
    # Git-Repo initialisieren
    repo = Repo.init(tmp_path)
    show_command(f"git init {tmp_path}")
    
    # Git Benutzer konfigurieren (wichtig für Commits)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    show_command("git config user.name 'Test User'")
    show_command("git config user.email 'test@example.com'")
    
    # Test-Datei erstellen
    test_file = tmp_path / "test.py"
    test_file.write_text("def test():\n    return 'test'")
    show_command(
        "echo 'def test():\\n    return \"test\"' > test.py",
        f"Datei erstellt: {test_file}"
    )
    
    # Datei stagen
    repo.index.add(["test.py"])
    show_command("git add test.py")
    
    return tmp_path

def test_analyze_command(test_repo):
    """
    Testet den 'analyze' Befehl
    
    Dieser Test prüft, ob:
    1. Der Befehl erfolgreich ausgeführt wird
    2. Die KI-Analyse korrekt durchgeführt wird
    """
    show_test_step("Teste 'analyze' Befehl")
    
    with runner.isolated_filesystem() as fs:
        # Test-Repo in isolierte Umgebung kopieren
        repo_path = Path(fs) / "repo"
        shutil.copytree(test_repo, repo_path)
        show_command(f"cp -r {test_repo} {repo_path}")
        
        # In Repo-Verzeichnis wechseln
        original_dir = os.getcwd()
        os.chdir(repo_path)
        
        try:
            # Befehl ausführen
            show_command("gitsynth analyze")
            result = runner.invoke(app, ["analyze"])
            
            # Ausgabe zeigen
            console.print(Panel(
                result.stdout or "Keine Ausgabe",
                title="[bold]Analyze Befehl Ausgabe"
            ))
            
            # Tests
            assert result.exit_code == 0, "Befehl sollte erfolgreich sein"
            assert "Analysiere Änderungen" in result.stdout, "Sollte Analyse-Meldung zeigen"
            console.print("[green]✓[/green] Analyze Test erfolgreich")
            
        finally:
            # Zurück zum ursprünglichen Verzeichnis
            os.chdir(original_dir)

def test_commit_command(test_repo):
    """
    Testet den 'commit' Befehl
    
    Dieser Test prüft zwei Szenarien:
    1. Automatischer Commit mit KI-generierter Message
    2. Commit mit manuell angegebener Message
    """
    show_test_step("Teste 'commit' Befehl")
    
    with runner.isolated_filesystem() as fs:
        # Test-Repo in isolierte Umgebung kopieren
        repo_path = Path(fs) / "repo"
        shutil.copytree(test_repo, repo_path)
        show_command(f"cp -r {test_repo} {repo_path}")
        
        # In Repo-Verzeichnis wechseln
        original_dir = os.getcwd()
        os.chdir(repo_path)
        
        try:
            # Test 1: Automatischer Commit
            show_command("gitsynth commit")
            console.print("[yellow]Simuliere Benutzer-Bestätigung mit 'y'[/yellow]")
            result = runner.invoke(app, ["commit"], input="y\n")
            
            console.print(Panel(
                result.stdout or "Keine Ausgabe",
                title="[bold]Automatischer Commit Ausgabe"
            ))
            assert result.exit_code == 0, "Befehl sollte erfolgreich sein"
            assert "Commit erstellt" in result.stdout, "Sollte Erfolgs-Meldung zeigen"
            
            # Neue Änderung für zweiten Test
            test_file = Path("test.py")
            test_file.write_text("def test():\n    return 'updated test'\n")
            repo = Repo(".")
            repo.index.add(["test.py"])
            show_command("echo 'updated test' > test.py && git add test.py")
            
            # Test 2: Manueller Commit
            show_command('gitsynth commit --message "test: Manual commit"')
            result = runner.invoke(app, ["commit", "--message", "test: Manual commit"])
            
            console.print(Panel(
                result.stdout or "Keine Ausgabe",
                title="[bold]Manueller Commit Ausgabe"
            ))
            assert result.exit_code == 0, "Befehl sollte erfolgreich sein"
            assert "Commit erstellt" in result.stdout, "Sollte Erfolgs-Meldung zeigen"
            
            console.print("[green]✓[/green] Commit Tests erfolgreich")
            
        finally:
            # Zurück zum ursprünglichen Verzeichnis
            os.chdir(original_dir)

def test_debug_command(test_repo):
    """
    Testet den 'debug' Befehl
    
    Dieser Test prüft, ob:
    1. Der Befehl erfolgreich ausgeführt wird
    2. Die Debug-Informationen korrekt durchgeführt werden
    """
    show_test_step("Teste 'debug' Befehl")
    
    with runner.isolated_filesystem() as fs:
        # Test-Repo in isolierte Umgebung kopieren
        repo_path = Path(fs) / "repo"
        shutil.copytree(test_repo, repo_path)
        show_command(f"cp -r {test_repo} {repo_path}")
        
        # In Repo-Verzeichnis wechseln
        original_dir = os.getcwd()
        os.chdir(repo_path)
        
        try:
            # Befehl ausführen
            show_command("gitsynth debug")
            result = runner.invoke(app, ["debug"])
            
            # Ausgabe zeigen
            console.print(Panel(
                result.stdout or "Keine Ausgabe",
                title="[bold]Debug Befehl Ausgabe"
            ))
            
            # Tests
            assert result.exit_code == 0, "Befehl sollte erfolgreich sein"
            assert "Debug-Informationen" in result.stdout, "Sollte Debug-Meldung zeigen"
            console.print("[green]✓[/green] Debug Test erfolgreich")
            
        finally:
            # Zurück zum ursprünglichen Verzeichnis
            os.chdir(original_dir)