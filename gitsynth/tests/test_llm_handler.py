import pytest
from ..core.ollama_handler import OllamaHandler, DiffAnalysis

class TestLLMDiffAnalysis:
    """Tests für LLM Analyse verschiedener Git Diff Typen.
    
    Diese Testklasse deckt alle möglichen Git Diff Szenarien ab:
    - Neue Dateien (new file mode)
    - Gelöschte Dateien (deleted file mode)
    - Umbenannte Dateien (rename from/to)
    - Modus-Änderungen (mode change)
    - Modifizierte Dateien (content changes)
    - Mehrere Änderungen gleichzeitig
    - Binärdateien
    """

    @pytest.fixture
    def llm(self):
        """Fixture für den OllamaHandler."""
        return OllamaHandler()

    def test_new_file_analysis(self, llm):
        """Test für Analyse einer neuen Datei.
        
        Prüft:
        - Erkennung von 'new file mode'
        - Korrekte change_type Zuweisung
        - Commit Type 'feat' für neue Features
        - 'Add' Verb in der Commit Message
        """
        diff = """
diff --git a/src/feature.ts b/src/feature.ts
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/src/feature.ts
@@ -0,0 +1,10 @@
+export class NewFeature {
+    constructor() {}
+    doSomething() {}
+}
"""
        analysis = llm.analyze_diff(diff)
        
        assert analysis["analysis"].files[0].change_type == "new"
        assert analysis["commit_type"] == "feat"
        assert "Add" in analysis["commit_message"]

    def test_deleted_file_analysis(self, llm):
        """Test für Analyse einer gelöschten Datei."""
        diff = """
diff --git a/old-feature.ts b/old-feature.ts
deleted file mode 100644
index 1234567..0000000
--- a/old-feature.ts
+++ /dev/null
@@ -1,10 +0,0 @@
-export class OldFeature {
-    constructor() {}
-    doSomething() {}
-}
"""
        analysis = llm.analyze_diff(diff)
        
        # Debug Output
        print("\n=== Complete Analysis Output ===")
        print(f"commit_type: {analysis['commit_type']}")
        print(f"commit_message: {analysis['commit_message']}")
        print(f"raw_analysis: {analysis['raw_analysis']}")
        print(f"analysis: {analysis['analysis'].model_dump_json(indent=2)}")
        print("===========================\n")
        
        assert analysis["analysis"].files[0].change_type == "deleted"
        assert "Remove" in analysis["commit_message"]

    def test_renamed_file_analysis(self, llm):
        """Test für Analyse einer umbenannten Datei.
        
        Prüft:
        - Erkennung von 'rename from/to'
        - Speicherung des alten Pfads
        - 'Rename' Verb in der Commit Message
        """
        diff = """
diff --git a/old-name.ts b/new-name.ts
similarity index 100%
rename from old-name.ts
rename to new-name.ts
"""
        analysis = llm.analyze_diff(diff)
        
        assert analysis["analysis"].files[0].change_type == "renamed"
        assert analysis["analysis"].files[0].old_path == "old-name.ts"
        assert "Rename" in analysis["commit_message"]

    def test_mode_change_analysis(self, llm):
        """Test für Analyse einer Modus-Änderung.
        
        Prüft:
        - Erkennung von mode changes (z.B. 100644 → 100755)
        - Korrekte change_type Zuweisung
        - 'Update' Verb für Modus-Änderungen
        """
        diff = """
diff --git a/script.sh b/script.sh
old mode 100644
new mode 100755
"""
        analysis = llm.analyze_diff(diff)
        
        assert analysis["analysis"].files[0].change_type == "mode_changed"
        assert "Update" in analysis["commit_message"]

    def test_modified_file_analysis(self, llm):
        """Test für Analyse einer modifizierten Datei.
        
        Prüft:
        - Erkennung von Inhaltänderungen
        - Korrekte change_type='modified'
        - Passende Commit Message basierend auf Änderungen
        """
        diff = """
diff --git a/src/feature.ts b/src/feature.ts
index 1234567..89abcde 100644
--- a/src/feature.ts
+++ b/src/feature.ts
@@ -1,5 +1,6 @@
 export class Feature {
     constructor() {}
+    newMethod() {}
     oldMethod() {}
 }
"""
        analysis = llm.analyze_diff(diff)
        
        assert analysis["analysis"].files[0].change_type == "modified"
        assert "Update" in analysis["commit_message"]

    def test_binary_file_analysis(self, llm):
        """Test für Analyse von Binärdateien.
        
        Prüft:
        - Erkennung von Binary file changes
        - Korrekte Behandlung ohne Inhaltsdiff
        """
        diff = """
diff --git a/img/logo.png b/img/logo.png
new file mode 100644
index 0000000..1234567
Binary files /dev/null and b/img/logo.png differ
"""
        analysis = llm.analyze_diff(diff)
        
        assert analysis["analysis"].files[0].change_type == "new"
        assert "Binary" in analysis["analysis"].files[0].changes

    def test_multiple_changes_analysis(self, llm):
        """Test für Analyse mehrerer gleichzeitiger Änderungen.
        
        Prüft:
        - Erkennung aller Änderungen
        - Korrekte Zuordnung der change_types
        - Sinnvolle Zusammenfassung in der Commit Message
        """
        diff = """
diff --git a/new-file.ts b/new-file.ts
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/new-file.ts
@@ -0,0 +1,5 @@
+export class NewFeature {}

diff --git a/old-file.ts b/old-file.ts
deleted file mode 100644
index 1234567..0000000
--- a/old-file.ts
+++ /dev/null
@@ -1,5 +0,0 @@
-export class OldFeature {}
"""
        analysis = llm.analyze_diff(diff)
        
        assert len(analysis["analysis"].files) == 2
        assert any(f.change_type == "new" for f in analysis["analysis"].files)
        assert any(f.change_type == "deleted" for f in analysis["analysis"].files) 

    def test_empty_diff_analysis(self, llm):
        """Test für leeren Diff.
        
        Prüft:
        - Korrekte Fehlerbehandlung
        - Sinnvolle Fehlermeldung
        """
        diff = ""
        analysis = llm.analyze_diff(diff)
        
        assert "error" in analysis["raw_analysis"].lower()

    def test_submodule_changes(self, llm):
        """Test für Submodule Änderungen.
        
        Prüft:
        - Erkennung von Submodule Updates
        - Korrekte change_type Zuweisung
        - Submodule Hash-Änderungen
        - Update Commit Message
        """
        diff = """
diff --git a/.gitmodules b/.gitmodules
index 1234567..89abcde 100644
--- a/.gitmodules
+++ b/.gitmodules
@@ -1,3 +1,6 @@
 [submodule "libs/core"]
     path = libs/core
     url = git@github.com:org/core.git
+[submodule "libs/utils"]
+    path = libs/utils
+    url = git@github.com:org/utils.git
diff --git a/libs/core b/libs/core
index aaa111...bbb222 160000
--- a/libs/core
+++ b/libs/core
@@ -1 +1 @@
-Subproject commit aaa111
+Subproject commit bbb222
"""
        analysis = llm.analyze_diff(diff)
        
        assert len(analysis["analysis"].files) == 2
        assert any("submodule" in f.changes.lower() for f in analysis["analysis"].files)
        assert "Update" in analysis["commit_message"]

    def test_merge_conflict_analysis(self, llm):
        """Test für Merge Konflikt Änderungen.
        
        Prüft:
        - Erkennung von Konfliktmarkierungen
        - Korrekte Analyse der Konfliktlösung
        - Passende Commit Message für Merges
        """
        diff = """
diff --git a/src/feature.ts b/src/feature.ts
index 1234567..89abcde 100644
--- a/src/feature.ts
+++ b/src/feature.ts
@@@ -1,7 -1,7 +1,7 @@@
  export class Feature {
-<<<<<<< HEAD
+     // Resolved conflict
      async process() {
-=======
-     async processData() {
->>>>>>> feature/new-api
+     async processWithValidation() {
      }
  }
"""
        analysis = llm.analyze_diff(diff)
        
        assert analysis["analysis"].files[0].change_type == "modified"
        assert "conflict" in analysis["analysis"].files[0].changes.lower()
        assert "Resolve" in analysis["commit_message"]

    def test_complex_multiple_changes(self, llm):
        """Test für komplexe mehrfache Änderungen.
        
        Prüft:
        - Mix aus verschiedenen Änderungstypen:
          * Neue Dateien
          * Gelöschte Dateien
          * Umbenennungen
          * Modus-Änderungen
          * Submodule Updates
        - Korrekte Erkennung aller Änderungen
        - Sinnvolle Zusammenfassung in der Commit Message
        """
        diff = """
diff --git a/src/new-feature.ts b/src/new-feature.ts
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/src/new-feature.ts
@@ -0,0 +1,10 @@
+export class NewFeature {}

diff --git a/src/old-feature.ts b/src/old-feature.ts
deleted file mode 100644
index 1234567..0000000
--- a/src/old-feature.ts
+++ /dev/null
@@ -1,10 +0,0 @@
-export class OldFeature {}

diff --git a/src/utils.ts b/src/helpers.ts
similarity index 100%
rename from src/utils.ts
rename to src/helpers.ts

diff --git a/scripts/deploy.sh b/scripts/deploy.sh
old mode 100644
new mode 100755

diff --git a/libs/core b/libs/core
index aaa111..bbb222 160000
--- a/libs/core
+++ b/libs/core
@@ -1 +1 @@
-Subproject commit aaa111
+Subproject commit bbb222
"""
        analysis = llm.analyze_diff(diff)
        
        # Prüfe Anzahl der Änderungen
        assert len(analysis["analysis"].files) == 5
        
        # Prüfe verschiedene Änderungstypen
        changes = [f.change_type for f in analysis["analysis"].files]
        assert "new" in changes
        assert "deleted" in changes
        assert "renamed" in changes
        assert "mode_changed" in changes
        
        # Prüfe Commit Message
        assert analysis["commit_type"] == "feat"  # Wegen neuer Feature-Datei
        assert any(word in analysis["commit_message"].lower() 
                  for word in ["update", "add", "restructure"])