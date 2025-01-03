import pytest
from ..core.git import GitHandler

class TestGitDiffCases:
    """Tests für verschiedene Git Diff Szenarien"""
    
    def test_new_file(self, tmp_path):
        """Test für neue Datei"""
        git = GitHandler(tmp_path)
        
        # Neue Datei erstellen
        file_path = tmp_path / "new.txt"
        file_path.write_text("new content")
        
        # Stage und prüfe Diff
        git.run_command("add", str(file_path))
        diff = git.get_staged_diff()
        
        assert "new file mode" in diff
        assert "+new content" in diff

    def test_deleted_file(self, tmp_path):
        """Test für gelöschte Datei"""
        git = GitHandler(tmp_path)
        
        # Datei erstellen und committen
        file_path = tmp_path / "delete.txt"
        file_path.write_text("content")
        git.run_command("add", str(file_path))
        git.run_command("commit", "-m", "add file")
        
        # Datei löschen
        file_path.unlink()
        git.run_command("add", str(file_path))
        diff = git.get_staged_diff()
        
        assert "deleted file mode" in diff

    def test_renamed_file(self, tmp_path):
        """Test für umbenannte Datei"""
        git = GitHandler(tmp_path)
        
        # Datei erstellen und committen
        old_path = tmp_path / "old.txt"
        old_path.write_text("content")
        git.run_command("add", str(old_path))
        git.run_command("commit", "-m", "add file")
        
        # Datei umbenennen
        new_path = tmp_path / "new.txt"
        git.run_command("mv", str(old_path), str(new_path))
        diff = git.get_staged_diff()
        
        assert "rename from" in diff
        assert "rename to" in diff

    def test_mode_change(self, tmp_path):
        """Test für Modus-Änderung"""
        git = GitHandler(tmp_path)
        
        # Datei erstellen und committen
        file_path = tmp_path / "script.sh"
        file_path.write_text("#!/bin/bash\necho test")
        git.run_command("add", str(file_path))
        git.run_command("commit", "-m", "add script")
        
        # Modus ändern
        file_path.chmod(0o755)  # Ausführbar machen
        git.run_command("add", str(file_path))
        diff = git.get_staged_diff()
        
        assert "mode change" in diff
        assert "100644 → 100755" in diff