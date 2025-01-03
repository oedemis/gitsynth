# GitSynth 🚀

An intelligent CLI tool for automated Git commits, documentation, and changelog management with LLM support.

## Features 🎯

### Smart Commit Messages
- Automatic detection of commit types based on https://www.conventionalcommits.org/en/v1.0.0/
- Context-aware commit descriptions
- Git history-based suggestions

### Changelog Management
- Automatic CHANGELOG.md generation
- Categorized changes
- Commit linking

## Tech Stack 🛠

### Core
- LangChain: LLM Integration and Tools
- LangGraph: Agent Orchestration
- Ollama: Local LLM (Mistral or Llama2)
- Chroma: Vector store for Embeddings
- HuggingFace Embeddings (BAAI/bge-small-en-v1.5)

### Development
- Poetry: Dependency Management
- Typer: CLI Framework
- GitPython: Git Integration
- Rich: Terminal Formatting

## Quick Start 🏃‍♂️

The core/commit_agent.py script is the heart of the application.
Unfortunately, tools with Ollama didn't work, so it's a Chain.
For a detailed description, see [Domain Documentation](docs/domain.md).

## Installation

### Prerequisites
- Python 3.11+
- Poetry
- Git
- Ollama (for local LLM)

### Development Setup

1. **Clone repository**:
   ```bash
   git clone https://github.com/yourusername/gitsynth.git
   cd gitsynth
   ```

2. **Set Python version**:
   ```bash
   # If using Conda, deactivate first
   conda deactivate

   # Set Python 3.11 for Poetry
   poetry env use python3.11
   ```

3. **Install dependencies**:
   ```bash
   poetry install
   ```

4. **Activate development environment**:
   ```bash
   poetry shell
   ```

5. **Switch to any repo and stage changes**:
   ```bash
   git init
   git add .
   ```

6. **Start Gitsynth**:
   ```bash
   gitsynth agent commit
   ```

### Usage

After activating the Poetry shell:

```bash
# Create commit with changelog
gitsynth agent commit

# Analyze changes
gitsynth analyze

# Debug analysis
gitsynth debug or gitsynth agent commit --debug

# TODO: Show help
gitsynth --help
```

## Features

- 🤖 AI-powered commit analysis
- 📝 Intelligent commit messages
- 🎯 Conventional Commits support
- 🎨 Beautiful terminal output

## Troubleshooting

- **"Command not found: poetry"**: Reinstall Poetry or set PATH
- **Conda conflicts**: Run `conda deactivate` before using Poetry
- **Ollama errors**: Ensure Ollama is running (`ollama run llama3.2`)

## Architecture 🏗

### Agents
1. **CommitAgent**: Analyzes changes & generates commits

## 📋 Usage

```bash
# See the flow
gitsynth agent commit
```

## Roadmap 🗺

- [✅] Basic CLI Setup with Poetry & Typer
- [✅] Git Integration & Diff Analysis
- [✅ ❌] LangChain/LangGraph Agent System
- [✅] Chroma Vector Store Integration
- [✅] Ollama LLM Integration
- [✅] Initial Commit Message Generation
- [✅] Documentation Synchronization
- [❌] Changelog Management

## Contributing 🤝

Contributions are welcome!

## License 📄

MIT