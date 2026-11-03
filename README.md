# Secure Two-Phase Coding Assistant

A coding assistant built with the Google Antigravity Python SDK, featuring a deterministic phase orchestrator.

## Local browser UI

Start the UI from the project root after installing dependencies:

```bash
python -m ui.server
```

Open `http://127.0.0.1:8765/`. The **Attack probe** lets you paste an HTTPS Wikipedia article URL, replace its page body with your own text, ask a question, and watch the live agent's MCP calls and containment report. The **Full build journey** runs Understanding → Init → Design → Coding → Review → Commit against an existing workspace. It streams logs, shows generated artifacts, and accepts `LGTM` or feedback when design review needs your input. To inject a custom page into that journey, select **Inject the page below into this journey**. Refreshing the page or clicking **Stop** terminates the active run and clears the browser view. The server accepts one active run at a time and binds only to loopback.

Under **Attack probe → Test type**, choose **Native boundary checks** to request real native file, directory, and shell tools against a synthetic Desktop outside a disposable workspace. This is an authorized enforcement test, separate from Wikipedia injection behavior. It records tool arguments, actual responses, and SDK runtime sandbox status in `report.md`, `report.json`, and `audit.jsonl`. No call, a model refusal, a startup error, or a test-guard denial is inconclusive—not sandbox proof. A successful synthetic read is reported as **BOUNDARY OPEN**. File-tool policy and OS command sandbox enforcement are different layers.

Choose **9 injection scenarios** to run all built-in decoy cases. These measure model behavior and decoy containment, not native sandbox enforcement.

Enter a model key in the UI for a single run or configure `GEMINI_API_KEY` in `.env`. The key is passed to the child process and is not written to the report. The full journey can stash workspace changes and merge an approved task branch, so choose the target workspace deliberately.

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
   Existing repositories must have a local `main` branch. Initialization stashes existing changes, switches to `main`, then creates the task branch; the stash stays separate for the user to restore later. For a workspace without Git, initialization commits its starting files on `main` before creating the task branch.
   Agent conversations compact at 300,000 tokens by default. Use `--compaction-threshold 50000` to choose a different threshold.
   Agents use `gemini-3.8-flash` by default; the design generator uses `gemini-4-argon`. Set `MODEL` or `DESIGN_MODEL` in `.env`, or pass `--model` or `--design-model`, to override them.
   In sandbox mode, agents can read HTTPS Wikipedia pages with the URL reader. Other URL reads and web searches are blocked. Terminal access is enabled with the SDK's OS command sandbox requested.
   The design and coding agents load `skills/wikipedia-research/SKILL.md` to search and follow Wikipedia pages when a task needs outside background facts. They should disclose when Wikipedia cannot establish a current fact.

## Mock Wikipedia and attack lab

Use `--mock-mode` to route the design and coding agents' Wikipedia research through a local stdio MCP server. The server offers `search_wikipedia` and `read_wikipedia_page` from the allowlisted files in `mock_pages/manifest.json`. In this mode, the agent's live URL reader, web search, and shell command tools are removed. The code agent can still use its host-provided Python validation tool. Mock pages are untrusted data and cannot approve a design or code review.

```bash
python main.py --mock-mode --workspace /path/to/disposable/project
python main.py --mock-mode --mock-pages-dir /path/to/custom/pages --workspace /path/to/disposable/project
python -m pytest -q tests/test_mock_smoke.py tests/test_attack_lab.py
python -m attack_lab.run --mode demo
python -m attack_lab.run --mode live  # Requires a valid GEMINI_API_KEY
```

A custom fixture directory needs `manifest.json` mapping exact `https://en.wikipedia.org/wiki/...` URLs to local Markdown files inside that directory. The [attack lab](attack_lab/README.md) runs nine distinct scenarios with inert decoy tools and a report that separates model behavior from containment. The standard project mock mode is a research and tool-routing simulation. Use a disposable workspace for a full pipeline run because the host's coding validation tool executes generated Python tests.

## Structure
- `config/`: Startup flags and configuration loader (`.env` + terminal args).
- `prompts/`: Markdown system prompts for agents.
- `src/orchestrator.py`: Deterministic phase controller (Understanding, Init, Design, Coding, Review, Commit).
- `src/coding_tools.py`: Host-side tools for the coding agent. One reports workspace files and Git changes; the other compiles supplied Python paths and runs pytest on supplied test paths (for example, `tests`).
- `src/coding_phase.py`: Coding agent that consumes requirements and the approved design, then validates its changes.
- `main.py`: Command line interface.

## Onboarding

See [docs/ONBOARDING.md](docs/ONBOARDING.md) for the full architecture, workflow rationale, security boundaries, artifacts, operating instructions, and extension guidance.
