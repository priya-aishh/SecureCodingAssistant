from pathlib import Path
from config.settings import StartupFlags
from google.antigravity import LocalAgentConfig, CapabilitiesConfig
from google.antigravity.hooks import policy


class EnvironmentManager:
    """Sets up the workspace environment and Antigravity sandbox."""

    def __init__(self, flags: StartupFlags):
        self.flags = flags
        self.project_path = Path(flags.project_dir).resolve()

    def setup_workspace(self) -> Path:
        self.project_path.mkdir(parents=True, exist_ok=True)
        return self.project_path

    def build_sandbox_config(
        self,
        instructions: str = "",
        model: str = "",
        tools: list = None,
        policies: list = None,
    ) -> LocalAgentConfig:
        self.setup_workspace()

        active_policies = []
        if self.flags.sandbox:
            active_policies.extend(policy.workspace_only([str(self.project_path)]))
        if policies:
            active_policies.extend(policies)

        return LocalAgentConfig(
            system_instructions=instructions,
            model=model or self.flags.model,
            api_key=self.flags.gemini_api_key or None,
            workspaces=[str(self.project_path)],
            policies=active_policies,
            tools=tools,
            capabilities=CapabilitiesConfig(),
        )

    def print_status(self) -> None:
        print(f"[Init] Mounted Project: {self.project_path}")
        print(f"[Init] Sandbox: {'RESTRICTED' if self.flags.sandbox else 'HOST'}")
