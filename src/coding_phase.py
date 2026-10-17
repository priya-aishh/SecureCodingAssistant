"""Implementation phase driven by the approved design."""

import asyncio
import json
from pathlib import Path

from google.antigravity import Agent, BuiltinTools, CapabilitiesConfig

from config.settings import StartupFlags
from src.coding_tools import CodingTools
from src.environment import EnvironmentManager


CODING_TOOLS = CapabilitiesConfig(
    enable_subagents=False,
    enabled_tools=[
        BuiltinTools.LIST_DIR,
        BuiltinTools.SEARCH_DIR,
        BuiltinTools.FIND_FILE,
        BuiltinTools.VIEW_FILE,
        BuiltinTools.CREATE_FILE,
        BuiltinTools.EDIT_FILE,
        BuiltinTools.RUN_COMMAND,
        BuiltinTools.READ_URL_CONTENT,
    ],
)


class CodingPhase:
    """Ask an agent to implement, test, and report the approved change."""

    def __init__(self, flags: StartupFlags, env: EnvironmentManager):
        self.env = env
        self.artifacts_dir = Path(flags.artifacts_dir).resolve()
        self.prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "coding.md"
        self.style_skill_path = Path(__file__).resolve().parent.parent / "skills" / "coding-style" / "SKILL.md"
        self.tools = CodingTools(env.workspace_path)

    async def _run(self, requirements: str, design: str, feedback: str = "") -> str:
        before = self.tools.workspace_snapshot()
        self.tools.last_python_result = None
        self.tools.last_validation_snapshot = None
        config = self.env.build_sandbox_config(
            instructions=(
                self.prompt_path.read_text(encoding="utf-8")
                + "\n\n# Coding style skill\n\n"
                + self.style_skill_path.read_text(encoding="utf-8")
            ),
            capabilities=CODING_TOOLS,
            tools=self.tools.agent_tools(),
        )
        message = (
            f"Mounted workspace: {self.env.workspace_path}\n\n"
            f"User requirements:\n{requirements}\n\n"
            f"Approved design document:\n{design}"
        )
        if feedback:
            message += f"\n\nCode reviewer feedback on the current implementation:\n{feedback}\nRevise the existing changes accordingly."
        async with Agent(config) as agent:
            response = await agent.chat(message)
            summary = "".join([token async for token in response]).strip()

        if not summary:
            raise RuntimeError("The coding agent returned an empty response.")
        after = self.tools.workspace_snapshot()
        changed = {path for path in before.keys() | after.keys() if before.get(path) != after.get(path)}
        status = self.tools.check_workspace()
        if status["is_empty"] or not changed or not status["git_changes"]:
            raise RuntimeError("The coding agent reported completion without workspace changes.")
        if not feedback and not any(
            path.endswith(".py")
            and ("tests" in Path(path).parts or Path(path).name.startswith("test_") or path.endswith("_test.py"))
            for path in changed
        ):
            raise RuntimeError("The coding agent did not add or update a Python unit test.")
        if not self.tools.last_python_result or not self.tools.last_python_result["passed"]:
            raise RuntimeError("The coding agent did not complete passing Python compile and unit-test checks.")
        if self.tools.last_validation_snapshot != after:
            raise RuntimeError("The coding agent changed files after its last Python checks.")
        checked_paths = self.tools.last_python_result["source_paths"] + self.tools.last_python_result["test_paths"]
        test_paths = self.tools.last_python_result["test_paths"]

        def covered(path: str, selections: list[str]) -> bool:
            file = self.env.workspace_path / path
            return any(file.is_relative_to((self.env.workspace_path / selected).resolve()) for selected in selections)

        if any(path.endswith(".py") and not covered(path, checked_paths) for path in changed):
            raise RuntimeError("The Python checks did not include every changed Python file.")
        if any(
            path.endswith(".py")
            and ("tests" in Path(path).parts or Path(path).name.startswith("test_") or path.endswith("_test.py"))
            and not covered(path, test_paths)
            for path in changed
        ):
            raise RuntimeError("The unit-test run did not include the changed tests.")

        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        summary_file = self.artifacts_dir / "coding_summary.md"
        summary_file.write_text(summary + "\n", encoding="utf-8")
        validation_file = self.artifacts_dir / "coding_validation.json"
        validation_file.write_text(
            json.dumps(
                {"changed_files": sorted(changed), "workspace": status, "python_checks": self.tools.last_python_result},
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        print(f"[Coding] Changes and checks completed. Summary: {summary_file}; validation: {validation_file}")
        return summary

    def run(self, requirements: str, design: str, feedback: str = "") -> str:
        return asyncio.run(self._run(requirements, design, feedback))
