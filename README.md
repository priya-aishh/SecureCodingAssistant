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
   After approval, the coding agent implements the design, writes unit tests, and uses the workspace and Python validation tools. The pipeline stops if it reports no changes or does not complete passing checks. The host saves `coding_summary.md` and `coding_validation.json` under the artifacts directory.
   The code reviewer checks the full workspace diff against the requirements and human-approved design. It records findings in `coding_review.md` and saves the diff as `coding_diff.patch`. The coding and review phases can repeat for up to six rounds using reviewer feedback. Approval commits the task branch and merges it into `main` locally; otherwise, the pipeline hands the branch and findings to the user without committing.
   Existing repositories must have a local `main` branch, a clean Git index, and no existing code changes when the task starts. For a workspace without Git, initialization commits its starting files on `main` before creating the task branch.
   Agent conversations compact at 300,000 tokens by default. Use `--compaction-threshold 50000` to choose a different threshold.
   Agents use `gemini-3.8-flash` by default; the design generator uses `gemini-4-argon`. Set `MODEL` or `DESIGN_MODEL` in `.env`, or pass `--model` or `--design-model`, to override them.
   In sandbox mode, agents can read HTTPS Wikipedia pages with the URL reader. Other URL reads and web searches are blocked. Terminal access is enabled with the SDK's OS command sandbox requested.
   The design and coding agents load `skills/wikipedia-research/SKILL.md` to search and follow Wikipedia pages when a task needs outside background facts. They should disclose when Wikipedia cannot establish a current fact.

## Structure
- `config/`: Startup flags and configuration loader (`.env` + terminal args).
- `prompts/`: Markdown system prompts for agents.
- `src/orchestrator.py`: Deterministic phase controller (Understanding, Init, Design, Coding, Review, Commit).
- `src/coding_tools.py`: Host-side tools for the coding agent. One reports workspace files and Git changes; the other compiles supplied Python paths and runs pytest on supplied test paths (for example, `tests`).
- `src/coding_phase.py`: Coding agent that consumes requirements and the approved design, then validates its changes.
- `main.py`: Command line interface.
