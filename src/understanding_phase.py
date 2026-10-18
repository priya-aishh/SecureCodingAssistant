import asyncio
import sys
from pathlib import Path

from google.antigravity import Agent, CapabilitiesConfig

from config.settings import StartupFlags
from src.agent_output import collect_response
from src.environment import EnvironmentManager


class UnderstandingPhase:
    """Turn a feature description into a short task document."""

    def __init__(self, flags: StartupFlags, env: EnvironmentManager):
        self.env = env
        self.artifacts_dir = Path(flags.artifacts_dir).resolve()
        self.prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "understanding.md"

    async def _elicit(self, task: str) -> str:
        instructions = self.prompt_path.read_text(encoding="utf-8")
        config = self.env.build_sandbox_config(
            instructions=instructions,
            capabilities=CapabilitiesConfig(enable_subagents=False, enabled_tools=[]),
            tool_log_phase="Understanding",
        )

        async with Agent(config) as agent:
            return await collect_response(agent, f"Feature description: {task}", "Understanding")

    def run(self, task: str) -> str:
        task = task.strip()
        if not task and sys.stdin.isatty():
            try:
                task = input("[Understanding] Describe the feature you want to implement: ").strip()
            except (EOFError, KeyboardInterrupt):
                task = ""
        if not task:
            print("[Understanding] No task provided.")
            return ""

        print(f"\n[Understanding] Task: {task}")
        content = asyncio.run(self._elicit(task))
        if not content:
            raise RuntimeError("The understanding agent returned an empty response.")

        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        task_file = self.artifacts_dir / "task.md"
        task_file.write_text(content + "\n", encoding="utf-8")
        print(f"[Understanding] Requirements saved to: {task_file}")
        return content
