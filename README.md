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
   python main.py
   ```
   The understanding phase asks for a feature description and saves a short `task.md`. Use `-p "Your task description"` to provide the description on the command line.
   The design phase inspects the mounted workspace, writes `design.md`, and records up to six generator and reviewer rounds per feedback cycle in `design_review.md`. It then asks for human approval. Type `LGTM` to approve or give feedback for another revision. Without an interactive terminal, the pipeline stops with approval pending.

## Structure
- `config/`: Startup flags and configuration loader (`.env` + terminal args).
- `prompts/`: Markdown system prompts for agents.
- `src/orchestrator.py`: Deterministic phase controller (Understanding, Init, Design, Coding, Commit).
- `main.py`: Command line interface.
