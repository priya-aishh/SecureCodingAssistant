from config.settings import StartupFlags
from src.init_phase import InitPhase
from src.environment import EnvironmentManager
from src.understanding_phase import UnderstandingPhase
from src.design_phase import DesignPhase
from src.coding_phase import CodingPhase


class Orchestrator:
    """Deterministic orchestrator managing task lifecycle phases."""

    def __init__(self, flags: StartupFlags):
        self.flags = flags
        self.init_phase_handler = InitPhase(flags)
        self.env_manager = EnvironmentManager(flags)
        self.understanding_handler = UnderstandingPhase(flags, self.env_manager)
        self.design_handler = DesignPhase(flags, self.env_manager)
        self.coding_handler = CodingPhase(flags, self.env_manager)

    def init_phase(self) -> None:
        """Init phase: prepare git repository/branch and verify environment status."""
        self.init_phase_handler.run()
        self.env_manager.print_status()

    def understanding_phase(self, task: str) -> str:
        """Understanding phase: gather user requirements and write to artifacts."""
        return self.understanding_handler.run(task)

    def design_phase(self, requirements: str) -> str | None:
        """Design phase: generate, review, and seek human approval."""
        return self.design_handler.run(requirements)

    def coding_phase(self, requirements: str, design: str) -> str:
        """Coding phase: implement the approved design and validate it."""
        return self.coding_handler.run(requirements, design)

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
        requirements = self.understanding_phase(task)
        if not requirements:
            return
        self.init_phase()
        design = self.design_phase(requirements)
        if design is None:
            return
        self.coding_phase(requirements, design)
        self.review_phase()
        self.commit_phase()
