from pathlib import Path
from config.settings import StartupFlags
from google.antigravity import LocalAgentConfig, CapabilitiesConfig
from google.antigravity.hooks import policy


class EnvironmentManager:
    """Manages workspace mounting, artifacts directory, and Antigravity sandbox config."""

    def __init__(self, flags: StartupFlags):
        self.flags = flags

        # 1. Target project workspace
        self.workspace_path = Path(flags.workspace_dir).resolve()
        if not self.workspace_path.exists():
            raise FileNotFoundError(f"Target workspace not found: {self.workspace_path}")

        # 2. Intermediate artifacts directory (/tmp/artifacts for designs, diffs, logs)
        self.artifacts_path = Path(flags.artifacts_dir).resolve()
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

    def build_sandbox_config(
        self,
        instructions: str = "",
        model: str = "",
        tools: list = None,
        policies: list = None,
        capabilities: CapabilitiesConfig = None,
    ) -> LocalAgentConfig:
        """Configures sandbox mounting for the target workspace and intermediate artifacts."""
        active_policies = []
        if self.flags.sandbox:
            active_policies.extend(policy.workspace_only([str(self.workspace_path)]))
        if policies:
            active_policies.extend(policies)

        return LocalAgentConfig(
            system_instructions=instructions,
            model=model or self.flags.model,
            api_key=self.flags.gemini_api_key or None,
            workspaces=[str(self.workspace_path)],
            policies=active_policies,
            tools=tools,
            capabilities=capabilities or CapabilitiesConfig(),
            save_dir=str(self.artifacts_path),
        )

    def print_status(self) -> None:
        print(f"[Init] Workspace (Mounted): {self.workspace_path}")
        print(f"[Init] Artifacts Directory: {self.artifacts_path}")
        print(f"[Init] Sandbox Isolation: {'RESTRICTED' if self.flags.sandbox else 'HOST'}")
