# Secure Two-Phase Coding Assistant

A coding assistant built with the Google Antigravity Python SDK, featuring a deterministic phase orchestrator.

## Quickstart

1. **Install dependencies**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure API key**:
   ```bash
   cp .env.example .env
   # Add your GEMINI_API_KEY to .env
   ```

3. **Run**:
   ```bash
   python main.py -p "Your task description"
   ```

## Structure
- `config/`: Startup flags and configuration loader (`.env` + terminal args).
- `prompts/`: Markdown system prompts for agents.
- `src/orchestrator.py`: Deterministic phase controller (Init, Understanding, Design, Coding, Commit).
- `main.py`: Command line interface.
