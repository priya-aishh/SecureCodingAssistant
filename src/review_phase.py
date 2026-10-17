"""Review the implementation against the approved design."""

import asyncio
import difflib
import subprocess
from pathlib import Path

from google.antigravity import Agent, BuiltinTools, CapabilitiesConfig

from config.settings import StartupFlags
from src.environment import EnvironmentManager


REVIEW_TOOLS = CapabilitiesConfig(
    enable_subagents=False,
    enabled_tools=[
        BuiltinTools.LIST_DIR,
        BuiltinTools.SEARCH_DIR,
        BuiltinTools.FIND_FILE,
        BuiltinTools.VIEW_FILE,
    ],
)


class ReviewPhase:
    def __init__(self, flags: StartupFlags, env: EnvironmentManager):
        self.env = env
        self.workspace = Path(flags.workspace_dir).resolve()
        self.artifacts_dir = Path(flags.artifacts_dir).resolve()
        self.prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "code_reviewer.md"

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=self.workspace, capture_output=True, text=True, check=True
        )
        return result.stdout

    def diff(self) -> str:
        """Include tracked changes and new files without modifying the Git index."""
        paths = ["."]
        if self.artifacts_dir != self.workspace and self.artifacts_dir.is_relative_to(self.workspace):
            artifact_path = self.artifacts_dir.relative_to(self.workspace).as_posix()
            paths.append(f":(exclude){artifact_path}/**")
        try:
            tracked = self._git("diff", "HEAD", "--", *paths)
        except subprocess.CalledProcessError:
            tracked = self._git("diff", "--", *paths) + self._git("diff", "--cached", "--", *paths)

        new_files = self._git("ls-files", "--others", "--exclude-standard", "-z", "--", *paths).split("\0")
        additions = []
        for name in filter(None, new_files):
            path = (self.workspace / name).resolve()
            if not path.is_relative_to(self.workspace) or path.is_relative_to(self.artifacts_dir):
                continue
            if not path.is_file():
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            except UnicodeError:
                additions.append(f"New binary file: {name}\n")
                continue
            if not lines:
                additions.append(f"New empty file: {name}\n")
                continue
            additions.extend(difflib.unified_diff([], lines, fromfile="/dev/null", tofile=f"b/{name}"))
        return tracked + "".join(additions)

    async def _run(self, requirements: str, design: str, summary: str) -> str:
        """Return an agent verdict and actionable findings."""
        diff = self.diff()
        if not diff.strip():
            raise RuntimeError("No changes are available for code review.")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        diff_file = self.artifacts_dir / "coding_diff.patch"
        diff_file.write_text(diff, encoding="utf-8")
        validation_file = self.artifacts_dir / "coding_validation.json"
        validation = validation_file.read_text(encoding="utf-8") if validation_file.exists() else "Unavailable"
        config = self.env.build_sandbox_config(
            instructions=self.prompt_path.read_text(encoding="utf-8"),
            capabilities=REVIEW_TOOLS,
        )
        message = (
            f"Mounted workspace: {self.workspace}\n\n"
            f"User requirements:\n{requirements}\n\n"
            f"Human-approved design:\n{design}\n\n"
            f"Coding agent summary:\n{summary}\n\n"
            f"Host-side coding validation:\n{validation}\n\n"
            f"Full workspace diff:\n{diff}"
        )
        async with Agent(config) as agent:
            response = await agent.chat(message)
            review = "".join([token async for token in response]).strip()
        if not review:
            raise RuntimeError("The code reviewer returned an empty response.")
        with (self.artifacts_dir / "coding_review.md").open("a", encoding="utf-8") as log:
            log.write(f"\n## Code review\n{review}\n")
        print(f"[Review] Diff: {diff_file}\n[Review] Result:\n{review}\n")
        return review

    def run(self, requirements: str, design: str, summary: str) -> str:
        return asyncio.run(self._run(requirements, design, summary))
