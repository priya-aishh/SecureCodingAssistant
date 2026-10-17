import subprocess
import uuid
from pathlib import Path
from config.settings import StartupFlags


class InitPhase:
    """Prepares the workspace git repository and checks out a unique task branch."""

    def __init__(self, flags: StartupFlags):
        self.flags = flags
        self.workspace = Path(flags.workspace_dir).resolve()
        self.branch_name = ""

    def run(self) -> None:
        """Initializes git if needed, discards uncommitted changes, and checks out a unique branch."""
        # 1. Initialize git if not present
        if not (self.workspace / ".git").exists():
            subprocess.run(["git", "init"], cwd=self.workspace, capture_output=True, check=True)
            print(f"[Init] Initialized Git repository in {self.workspace}")

        # 2. Discard uncommitted changes
        subprocess.run(["git", "checkout", "--", "."], cwd=self.workspace, capture_output=True)
        subprocess.run(["git", "clean", "-fd"], cwd=self.workspace, capture_output=True)

        # 3. Create unique branch with UUID
        short_id = uuid.uuid4().hex[:8]
        self.branch_name = f"task-{short_id}"
        subprocess.run(["git", "checkout", "-b", self.branch_name], cwd=self.workspace, capture_output=True)
        print(f"[Init] Created and checked out branch '{self.branch_name}'")
