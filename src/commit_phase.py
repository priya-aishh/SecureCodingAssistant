"""Commit reviewed changes and fast-forward main to the task branch."""

import json
import subprocess
from pathlib import Path

from config.settings import StartupFlags
from src.init_phase import InitPhase


class CommitPhase:
    def __init__(self, flags: StartupFlags, init_phase: InitPhase):
        self.workspace = Path(flags.workspace_dir).resolve()
        self.artifacts = Path(flags.artifacts_dir).resolve()
        self.init_phase = init_phase

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=self.workspace, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()

    def run(self) -> None:
        branch = self.init_phase.branch_name
        if not branch or self._git("branch", "--show-current") != branch:
            raise RuntimeError("The task branch is not checked out; refusing to commit.")
        if self._git("diff", "--cached", "--name-only"):
            raise RuntimeError("Unexpected staged changes exist; refusing to commit.")
        validation = json.loads((self.artifacts / "coding_validation.json").read_text(encoding="utf-8"))
        if not validation["python_checks"]["passed"]:
            raise RuntimeError("Python checks have not passed; refusing to commit.")
        paths = validation["changed_files"]
        if not paths or any(
            not (self.workspace / path).resolve().is_relative_to(self.workspace)
            or (self.workspace / path).resolve().is_relative_to(self.artifacts)
            for path in paths
        ):
            raise RuntimeError("The validated file list is missing or outside the workspace.")
        self._git("add", "-A", "--", *paths)
        staged = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=self.workspace, check=False
        )
        if staged.returncode != 1:
            raise RuntimeError("No reviewed changes are staged for commit.")
        self._git("commit", "-m", "Implement approved feature")
        commit = self._git("rev-parse", "--short", "HEAD")
        self._git("switch", "main")
        self._git("merge", "--ff-only", branch)
        print(f"[Commit] Committed {commit} on {branch} and merged into main.")
