import asyncio
import shutil
import sys
from pathlib import Path

from google.antigravity import Agent, BuiltinTools, CapabilitiesConfig
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule
from rich.text import Text

from config.settings import StartupFlags
from src.agent_output import collect_response
from src.environment import EnvironmentManager


DESIGN_TOOLS = CapabilitiesConfig(
    enable_subagents=False,
    enabled_tools=[
        BuiltinTools.LIST_DIR,
        BuiltinTools.SEARCH_DIR,
        BuiltinTools.FIND_FILE,
        BuiltinTools.VIEW_FILE,
        BuiltinTools.READ_URL_CONTENT,
        BuiltinTools.RUN_COMMAND,
    ],
)
MAX_DESIGN_ITERATIONS = 6


class DesignPhase:
    """Generate and review designs until the user approves one."""

    def __init__(self, flags: StartupFlags, env: EnvironmentManager):
        self.env = env
        self.console = Console(width=min(shutil.get_terminal_size((100, 24)).columns, 110))
        self.draft_number = 0
        self.review_started = False
        self.design_model = flags.design_model
        self.artifacts_dir = Path(flags.artifacts_dir).resolve()
        self.prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
        self.research_skill_path = Path(__file__).resolve().parent.parent / "skills" / "wikipedia-research" / "SKILL.md"

    def _show_document(self, title: str, content: str, path: Path, color: str) -> None:
        self.console.print()
        self.console.print(Rule(title, style=color))
        self.console.print(Markdown(content))
        self.console.print(Text(f"Saved to {path}", style="dim"))
        self.console.print()

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
            tool_log_phase="Design generator",
        )
        reviewer_config = self.env.build_sandbox_config(
            instructions=(self.prompts_dir / "design_reviewer.md").read_text(encoding="utf-8") + "\n\n" + research_skill,
            capabilities=DESIGN_TOOLS,
            tool_log_phase="Design reviewer",
        )
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        design_file = self.artifacts_dir / "design.md"
        review_file = self.artifacts_dir / "design_review.md"
        if not self.review_started:
            review_file.write_text("# Design Reviews\n", encoding="utf-8")
            self.review_started = True
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

        self.console.print(Text(f"[Design] Starting generator and reviewer loop (up to {MAX_DESIGN_ITERATIONS} rounds).", style="cyan"))
        async with Agent(generator_config) as generator, Agent(reviewer_config) as reviewer:
            for _ in range(MAX_DESIGN_ITERATIONS):
                self.draft_number += 1
                number = self.draft_number
                self.console.print(Text(f"[Design] Generating draft {number}...", style="cyan"))
                design = await collect_response(generator, message, "Design generator", self.console)
                if not design:
                    raise RuntimeError("The design generator returned an empty response.")
                design_file.write_text(design + "\n", encoding="utf-8")
                self._show_document(f"Design draft {number}", design, design_file, "cyan")
                self.console.print(Text(f"[Design] Reviewing draft {number}...", style="yellow"))
                review_message = (
                    f"Mounted workspace: {self.env.workspace_path}\n"
                    f"Requirements:\n{requirements}\n\n"
                    f"Design:\n{design}"
                )
                if feedback:
                    review_message += f"\n\nHuman feedback this draft must address:\n{feedback}"
                review = await collect_response(
                    reviewer,
                    review_message,
                    "Design reviewer",
                    self.console,
                )
                if not review:
                    raise RuntimeError("The design reviewer returned an empty response.")
                with review_file.open("a", encoding="utf-8") as log:
                    log.write(f"\n## Review {number}\n{review}\n")
                self._show_document(f"Reviewer comments {number}", review, review_file, "yellow")
                verdict = review.splitlines()[0].strip()
                self.console.print(Text(f"[Design] Round {number}: {verdict}", style="yellow"))
                if verdict == "APPROVED":
                    break
                message = (
                    "Revise the complete design using this reviewer feedback. "
                    "Inspect the workspace again where needed.\n\n"
                    f"Requirements:\n{requirements}\n\n"
                    f"Previous design:\n{design}\n\nReviewer feedback:\n{review}"
                )

        self.console.print(Text(f"[Design] Generator and reviewer loop complete after round {number}; awaiting your review.", style="cyan"))
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
