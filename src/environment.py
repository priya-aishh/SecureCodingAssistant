"""Environment setup and Antigravity sandbox configuration."""

from pathlib import Path
from typing import Any, Optional, Sequence
from config.settings import StartupFlags
from google.antigravity import LocalAgentConfig, CapabilitiesConfig
from google.antigravity.hooks import policy


class EnvironmentManager:
    """Sets up the working environment and configures the Antigravity sandbox mounting."""

    def __init__(self, flags: StartupFlags):
        self.flags = flags
        self.project_path = Path(flags.project_dir).resolve()

    def setup_workspace(self) -> Path:
        """Ensures the mounted project directory exists."""
        self.project_path.mkdir(parents=True, exist_ok=True)
        return self.project_path

    def build_sandbox_config(
        self,
        system_instructions: str = "",
        model: Optional[str] = None,
        tools: Optional[list[Any]] = None,
        policies: Optional[Sequence[Any]] = None,
        capabilities: Optional[CapabilitiesConfig] = None,
        **kwargs: Any,
    ) -> LocalAgentConfig:
        """Builds LocalAgentConfig with sandbox mounting and agent-specific tools, policies, and instructions."""
        self.setup_workspace()

        # Base sandbox policies: restrict file modifications to the mounted project folder
        combined_policies = []
        if self.flags.sandbox:
            combined_policies.extend(policy.workspace_only([str(self.project_path)]))

        # Merge any additional agent-specific policies
        if policies:
            combined_policies.extend(policies)

        return LocalAgentConfig(
            system_instructions=system_instructions,
            model=model or self.flags.model,
            api_key=self.flags.gemini_api_key or None,
            workspaces=[str(self.project_path)],
            policies=combined_policies,
            tools=tools,
            capabilities=capabilities or CapabilitiesConfig(),
            **kwargs,
        )

    def print_status(self) -> None:
        """Prints the initialized sandbox and mount status."""
        print(f"[Init] Mounted Project Folder: {self.project_path}")
        print(f"[Init] Sandbox Isolation: {'RESTRICTED (Network restricted, Workspace write-only)' if self.flags.sandbox else 'HOST (Unrestricted)'}")
