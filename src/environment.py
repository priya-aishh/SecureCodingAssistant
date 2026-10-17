"""Environment setup and Antigravity sandbox configuration."""

from pathlib import Path
from typing import Optional
from config.settings import StartupFlags

try:
    from google.antigravity import LocalAgentConfig, CapabilitiesConfig
    from google.antigravity.hooks import policy
    ANTIGRAVITY_AVAILABLE = True
except ImportError:
    ANTIGRAVITY_AVAILABLE = False


class EnvironmentManager:
    """Sets up the working environment and configures the Antigravity sandbox mounting."""

    def __init__(self, flags: StartupFlags):
        self.flags = flags
        self.project_path = Path(flags.project_dir).resolve()

    def setup_workspace(self) -> Path:
        """Ensures the mounted project directory exists."""
        self.project_path.mkdir(parents=True, exist_ok=True)
        return self.project_path

    def build_sandbox_config(self, system_instructions: str = "") -> Optional["LocalAgentConfig"]:
        """Builds LocalAgentConfig mounting only the project directory with sandbox policies."""
        if not ANTIGRAVITY_AVAILABLE:
            return None

        self.setup_workspace()

        # In sandbox mode: file modifications are restricted strictly to the mounted project folder,
        # and network access is restricted by default.
        policies = []
        if self.flags.sandbox:
            policies = policy.workspace_only([str(self.project_path)])

        return LocalAgentConfig(
            system_instructions=system_instructions,
            model=self.flags.model,
            api_key=self.flags.gemini_api_key or None,
            workspaces=[str(self.project_path)],
            policies=policies,
            capabilities=CapabilitiesConfig(),
        )

    def print_status(self) -> None:
        """Prints the initialized sandbox and mount status."""
        print(f"[Init] Mounted Project Folder: {self.project_path}")
        print(f"[Init] Sandbox Isolation: {'RESTRICTED (Network restricted, Workspace write-only)' if self.flags.sandbox else 'HOST (Unrestricted)'}")
