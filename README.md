# GitSynth 🚀

rm -rf .venv
poetry env use python3.11

Ein intelligentes CLI-Tool für automatisierte Git-Commits, Dokumentation und Changelog-Management mit LLM-Unterstützung.

## Features 🎯

### Smart Commit Messages
- Automatische Erkennung von Commit-Typen basierend auf https://www.conventionalcommits.org/en/v1.0.0/
- Kontextbewusste Commit-Beschreibungen
- Git-History-basierte Vorschläge

### Changelog-Management
- Automatische CHANGELOG.md Generierung
- Kategorisierte Änderungen
- Verknüpfung mit Commits

## Tech Stack 🛠

### Core
- LangChain: LLM Integration und Tools
- LangGraph: Agenten-Orchestrierung
- Ollama: Lokales LLM (Mistral oder Llama2)
- Chroma: Vektorstore für Embeddings
- HuggingFace Embeddings (BAAI/bge-small-en-v1.5)

### Development
- Poetry: Dependency Management
- Typer: CLI Framework
- GitPython: Git Integration
- Rich: Terminal Formatting

## Quick Start 🏃‍♂️
Das Skirpt core/commit_agent.py ist der Kern.
Leider hat tools mit Ollama nicht funktioniert, es ist also ein Chain.
Für eine detaillierte Beschreibung , siehe [Domain Documentation](docs/domain.md).

## Installation

### Voraussetzungen
- Python 3.11+
- Poetry
- Git
- Ollama (für lokales LLM)

### Entwicklungs-Setup

1. **Repository klonen**:
   ```bash
   git clone https://github.com/yourusername/gitsynth.git
   cd gitsynth
   ```

2. **Python-Version setzen**:
   ```bash
   # Wenn du Conda verwendest, erst deaktivieren
   conda deactivate

   # Python 3.11 für Poetry setzen
   poetry env use python3.11
   ```

3. **Dependencies installieren**:
   ```bash
   poetry install
   ```

4. **Entwicklungsumgebung aktivieren**:
   ```bash
   poetry shell
   ```
5. **Beliebiege Repo wechseln und änderungen stagen**:
   ```bash
   git init
   git add . 
   ```

6. **Gitsynth starten**:
   ```bash
   gitsynth agent commit
   ```


### Verwendung

Nach der Aktivierung der Poetry-Shell:

```bash
# Commit erstellen mit Changelog
gitsynth agent commit

# Änderungen analysieren
gitsynth analyze

# Debuggen analysieren
gitsynth debug oder gitsynth agent commit --debug

# TODO: Hilfe anzeigen
gitsynth --help
```

## Features

- 🤖 KI-gestützte Commit-Analyse
- 📝 Intelligente Commit-Messages
- 🎯 Conventional Commits Support
- 🎨 Schöne Terminal-Ausgaben


## Troubleshooting

- **"Command not found: poetry"**: Poetry neu installieren oder PATH setzen
- **Conda Konflikte**: `conda deactivate` vor Poetry-Nutzung
- **Ollama-Fehler**: Sicherstellen dass Ollama läuft (`ollama run llama2`)

## Architektur 🏗

### Agenten
1. **CommitAgent**: Analysiert Changes & generiert Commits


## 📋 Verwendung

```bash
# Siehe den Flow
gitsynth agent commit
```

## Roadmap 🗺

- [✅] Basic CLI Setup mit Poetry & Typer
- [✅] Git Integration & Diff-Analyse
- [✅ ❌] LangChain/LangGraph Agent-System
- [✅ ] Chroma Vector Store Integration
- [✅ ] Ollama LLM Integration
- [✅ ] Erste Commit-Message-Generation
- [✅ ] Dokumentations-Synchronisation
- [ ❌] Changelog-Management

## Contributing 🤝

Beiträge sind willkommen! 

## Lizenz 📄

MIT