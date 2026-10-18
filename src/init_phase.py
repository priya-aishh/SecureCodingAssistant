import subprocess
import uuid
from pathlib import Path
from config.settings import StartupFlags


class InitPhase:
    """Prepares the workspace git repository and checks out a unique task branch."""

    def __init__(self, flags: StartupFlags):
        self.flags = flags
        self.workspace = Path(flags.workspace_dir).resolve()
        self.artifacts = Path(flags.artifacts_dir).resolve()
        self.branch_name = ""

    def run(self) -> None:
        """Initializes git if needed and checks out a unique branch."""
        new_repo = not (self.workspace / ".git").exists()
        if new_repo:
            subprocess.run(["git", "init", "-b", "main"], cwd=self.workspace, capture_output=True, check=True)
            print(f"[Init] Initialized Git repository in {self.workspace}")

        paths = ["."]
        if self.artifacts != self.workspace and self.artifacts.is_relative_to(self.workspace):
            paths.append(f":(exclude){self.artifacts.relative_to(self.workspace).as_posix()}/**")
        if new_repo:
            subprocess.run(["git", "add", "-A", "--", *paths], cwd=self.workspace, capture_output=True, check=True)
            subprocess.run(
                ["git", "commit", "--allow-empty", "-m", "Initialize workspace"],
                cwd=self.workspace, capture_output=True, check=True,
            )
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all", "--", *paths],
            cwd=self.workspace, capture_output=True, text=True, check=True,
        )
        if status.stdout.strip():
            subprocess.run(
                ["git", "stash", "push", "--include-untracked", "-m", "Coding assistant: before task", "--", *paths],
                cwd=self.workspace, capture_output=True, text=True, check=True,
            )
            stash = subprocess.run(
                ["git", "rev-parse", "--short", "refs/stash"],
                cwd=self.workspace, capture_output=True, text=True, check=True,
            ).stdout.strip()
            print(f"[Init] Stashed existing changes as {stash}; they remain available in Git stash.")
        staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=self.workspace, check=False)
        if staged.returncode != 0:
            raise RuntimeError("The Git index has pre-existing staged changes. Commit or unstage them before starting a task.")
        subprocess.run(["git", "switch", "main"], cwd=self.workspace, capture_output=True, check=True)
        base = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=self.workspace, capture_output=True)
        if base.returncode != 0:
            subprocess.run(
                ["git", "commit", "--allow-empty", "-m", "Initialize main branch"],
                cwd=self.workspace, capture_output=True, check=True,
            )
        short_id = uuid.uuid4().hex[:8]
        self.branch_name = f"task-{short_id}"
        subprocess.run(["git", "switch", "-c", self.branch_name], cwd=self.workspace, capture_output=True, check=True)
        print(f"[Init] Created and checked out branch '{self.branch_name}'")
