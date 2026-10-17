from pathlib import Path
from config.settings import StartupFlags
from google.antigravity import LocalAgentConfig, CapabilitiesConfig
from google.antigravity.hooks import policy


class EnvironmentManager:
    """Manages workspace mounting, intermediate artifacts, and conversation state directories."""

    def __init__(self, flags: StartupFlags):
        self.flags = flags

        # 1. Target project workspace where code changes happen
        self.workspace_path = Path(flags.workspace_dir).resolve()
        if not self.workspace_path.exists():
            raise FileNotFoundError(f"Target workspace not found: {self.workspace_path}")

        # 2. Intermediate artifacts directory (/tmp/artifacts for designs, diffs, logs)
        self.artifacts_path = Path(flags.artifacts_dir).resolve()
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

        # 3. Conversation & session state directory (.gemini level)
        self.app_data_path = Path(flags.app_data_dir).resolve()
        self.app_data_path.mkdir(parents=True, exist_ok=True)

    def build_sandbox_config(
        self,
        instructions: str = "",
        model: str = "",
        tools: list = None,
        policies: list = None,
    ) -> LocalAgentConfig:
        """Configures sandbox mounting for the target workspace, intermediate artifacts, and conversation state."""
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
            capabilities=CapabilitiesConfig(),
            save_dir=str(self.artifacts_path),
            app_data_dir=str(self.app_data_path),
        )

    def print_status(self) -> None:
        print(f"[Init] Workspace (Mounted): {self.workspace_path}")
        print(f"[Init] Artifacts Directory: {self.artifacts_path}")
        print(f"[Init] Conversation Data: {self.app_data_path}")
        print(f"[Init] Sandbox Isolation: {'RESTRICTED' if self.flags.sandbox else 'HOST'}")
