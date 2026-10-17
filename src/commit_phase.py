"""Commit reviewed changes and fast-forward main to the task branch."""

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
        paths = ["."]
        if self.artifacts != self.workspace and self.artifacts.is_relative_to(self.workspace):
            paths.append(f":(exclude){self.artifacts.relative_to(self.workspace).as_posix()}/**")
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
