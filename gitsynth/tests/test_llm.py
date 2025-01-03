import pytest
from gitsynth.core.llm import LLMHandler, LLMHandlerError

def test_llm_handler_initialization():
    """Testet die grundlegende Initialisierung des LLMHandlers"""
    handler = LLMHandler()
    assert handler.chat_model is not None
    assert handler.embeddings is not None

def test_analyze_diff():
    """Testet die Analyse eines Git Diffs"""
    handler = LLMHandler()
    test_diff = """
    diff --git a/test.py b/test.py
    index 1234567..89abcdef 100644
    --- a/test.py
    +++ b/test.py
    @@ -1,3 +1,4 @@
     def test():
    -    return "old"
    +    return "new"
    """
    result = handler.analyze_diff(test_diff)
    print("\nLLM Analyse Ergebnis:", result)  # Zeigt die vollständige Analyse
    assert isinstance(result, dict)
    assert "commit_type" in result
    assert "analysis" in result
    print(f"\nErkannter Commit-Typ: {result['commit_type']}")
    print(f"Analyse: {result['analysis']}")
    
def test_embeddings():
    """Testet die Embedding-Generierung"""
    handler = LLMHandler()
    texts = ["This is a test", "Another test text"]
    embeddings = handler.get_embeddings(texts)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384  # all-MiniLM-L6-v2 hat 384 Dimensionen

@pytest.mark.skip(reason="Nur manuell ausführen wenn Ollama nicht läuft")
def test_llm_handler_initialization_failure():
    """Testet ob korrekte Fehler geworfen werden wenn Ollama nicht verfügbar ist"""
    with pytest.raises(LLMHandlerError):
        LLMHandler() 

def test_analyze_diff_with_multiple_files():
    """Testet die Analyse von mehreren Dateien"""
    handler = LLMHandler()
    test_diff = """
    diff --git a/README.md b/README.md
    +## New Documentation
    diff --git a/src/feature.py b/src/feature.py
    +// TODO: New feature
    """
    result = handler.analyze_diff(test_diff)
    
    # Prüfe Priorisierung
    assert result["commit_type"] == "feat", "Neue Feature-Datei sollte Priorität haben"
    assert "feature.py" in result["analysis"], "Wichtigste Änderung zuerst"
    assert "README.md" in result["analysis"], "Andere Änderungen auch erwähnt"