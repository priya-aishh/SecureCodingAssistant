import asyncio
import sys
from pathlib import Path

from google.antigravity import Agent, BuiltinTools, CapabilitiesConfig

from config.settings import StartupFlags
from src.environment import EnvironmentManager


DESIGN_TOOLS = CapabilitiesConfig(
    enable_subagents=False,
    enabled_tools=[
        BuiltinTools.LIST_DIR,
        BuiltinTools.SEARCH_DIR,
        BuiltinTools.FIND_FILE,
        BuiltinTools.READ_URL_CONTENT,
        BuiltinTools.RUN_COMMAND,
    ],
)
MAX_DESIGN_ITERATIONS = 6


async def _ask(agent: Agent, message: str) -> str:
    response = await agent.chat(message)
    text = "".join([token async for token in response]).strip()
    if not text:
        raise RuntimeError("A design agent returned an empty response.")
    return text


class DesignPhase:
    """Generate and review designs until the user approves one."""

    def __init__(self, flags: StartupFlags, env: EnvironmentManager):
        self.env = env
        self.design_model = flags.design_model
        self.artifacts_dir = Path(flags.artifacts_dir).resolve()
        self.prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
        self.research_skill_path = Path(__file__).resolve().parent.parent / "skills" / "wikipedia-research" / "SKILL.md"

    async def _run(
        self,
        requirements: str,
        feedback: str = "",
        previous_design: str = "",
        previous_review: str = "",
    ) -> tuple[str, str]:
        research_skill = self.research_skill_path.read_text(encoding="utf-8")
        generator_config = self.env.build_sandbox_config(
            instructions=(self.prompts_dir / "design_generator.md").read_text(encoding="utf-8") + "\n\n" + research_skill,
            model=self.design_model,
            capabilities=DESIGN_TOOLS,
        )
        reviewer_config = self.env.build_sandbox_config(
            instructions=(self.prompts_dir / "design_reviewer.md").read_text(encoding="utf-8") + "\n\n" + research_skill,
            capabilities=DESIGN_TOOLS,
        )
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        design_file = self.artifacts_dir / "design.md"
        review_file = self.artifacts_dir / "design_review.md"
        if not review_file.exists():
            review_file.write_text("# Design Reviews\n", encoding="utf-8")
        message = (
            f"Mounted workspace: {self.env.workspace_path}\n"
            f"Requirements:\n{requirements}"
        )
        if feedback:
            message += (
                f"\n\nPrevious design:\n{previous_design}"
                f"\n\nLatest reviewer feedback:\n{previous_review}"
                f"\n\nUser feedback:\n{feedback}"
            )

        async with Agent(generator_config) as generator, Agent(reviewer_config) as reviewer:
            for iteration in range(1, MAX_DESIGN_ITERATIONS + 1):
                print(f"[Design] Draft {iteration}")
                design = await _ask(generator, message)
                design_file.write_text(design + "\n", encoding="utf-8")
                review = await _ask(
                    reviewer,
                    f"Mounted workspace: {self.env.workspace_path}\n"
                    f"Requirements:\n{requirements}\n\n"
                    f"Design:\n{design}",
                )
                with review_file.open("a", encoding="utf-8") as log:
                    log.write(f"\n## Review {iteration}\n{review}\n")
                if review.splitlines()[0].strip() == "APPROVED":
                    break
                message = (
                    "Revise the complete design using this reviewer feedback. "
                    "Inspect the workspace again where needed.\n\n"
                    f"Requirements:\n{requirements}\n\n"
                    f"Previous design:\n{design}\n\nReviewer feedback:\n{review}"
                )

        return design, review

    def generate(
        self,
        requirements: str,
        feedback: str = "",
        previous_design: str = "",
        previous_review: str = "",
    ) -> tuple[str, str]:
        return asyncio.run(self._run(requirements, feedback, previous_design, previous_review))

    def run(self, requirements: str) -> str | None:
        """Keep revising the design until the user approves or input ends."""
        feedback = design = review = ""
        while True:
            design, review = self.generate(requirements, feedback, design, review)
            print(f"\n[Design] Review the draft at {self.artifacts_dir / 'design.md'}:\n\n{design}\n")
            print(f"[Design] Automated review:\n{review}\n")
            if not sys.stdin.isatty():
                return None
            try:
                feedback = input("[Design] Type LGTM to approve or describe what to change: ").strip()
            except (EOFError, KeyboardInterrupt):
                return None
            if feedback.upper() == "LGTM":
                with (self.artifacts_dir / "design_review.md").open("a", encoding="utf-8") as log:
                    log.write("\n## Human approval\nLGTM\n")
                return design
            if not feedback:
                return None
            with (self.artifacts_dir / "design_review.md").open("a", encoding="utf-8") as log:
                log.write(f"\n## Human feedback\n{feedback}\n")
