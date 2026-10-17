from pathlib import Path
from config.settings import StartupFlags
from src.environment import EnvironmentManager


class Orchestrator:
    """Deterministic orchestrator managing task lifecycle phases."""

    def __init__(self, flags: StartupFlags):
        self.flags = flags
        self.env_manager = EnvironmentManager(flags)
        self.prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "agent.md"

    def init_phase(self) -> None:
        """Init phase: initialize working environment and Antigravity sandbox."""
        self.env_manager.setup_workspace()
        self.env_manager.print_status()

    def understanding_phase(self, task: str) -> str:
        """Understanding phase: analyze user task."""
        print(f"[Understanding] Task received: {task}")
        # TODO: Deploy understanding agent
        return task

    def design_phase(self, task: str) -> None:
        """Design phase: plan changes."""
        print("[Design] Planning phase...")
        # TODO: Deploy planning and critic agents

    def coding_phase(self) -> None:
        """Coding phase: apply code edits and run tests."""
        print("[Coding] Execution phase...")
        # TODO: Deploy coder agent and reviewers

    def review_phase(self) -> None:
        """Review phase: Gerrit-style diff review before commit."""
        # TODO: Render code diff like Gerrit, collect user review comments,
        # and check for LGTM approval (if not LGTM, loop back to understanding phase).
        pass

    def commit_phase(self) -> None:
        """Commit phase: push verified changes to branch."""
        print("[Commit] Final approval and commit phase...")
        # TODO: Deploy git push tool

    def run(self, task: str) -> None:
        """Run through all pipeline phases sequentially."""
        self.init_phase()
        self.understanding_phase(task)
        self.design_phase(task)
        self.coding_phase()
        self.review_phase()
        self.commit_phase()
