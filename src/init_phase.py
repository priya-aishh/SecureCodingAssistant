import subprocess
from pathlib import Path
from config.settings import StartupFlags
from google.antigravity import LocalAgentConfig, CapabilitiesConfig
from google.antigravity.hooks import policy


class InitClass:
    """Handles workspace setup, simple git initialization, and Antigravity sandbox config."""

    def __init__(self, flags: StartupFlags):
        self.flags = flags
        self.workspace = Path(flags.workspace_dir).resolve()
        self.artifacts_dir = Path(flags.artifacts_dir).resolve()

    def run(self) -> None:
        """Prepares workspace and sets up git branch for development."""
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        # 1. Initialize git if not already present
        if not (self.workspace / ".git").exists():
            subprocess.run(["git", "init"], cwd=self.workspace, capture_output=True, check=True)
            print(f"[Init] Initialized Git repository in {self.workspace}")

        # 2. Discard any uncommitted changes
        subprocess.run(["git", "checkout", "--", "."], cwd=self.workspace, capture_output=True)
        subprocess.run(["git", "clean", "-fd"], cwd=self.workspace, capture_output=True)

        # 3. Create or switch to development branch
        branch = "agent-dev"
        subprocess.run(["git", "checkout", "-B", branch], cwd=self.workspace, capture_output=True)
        print(f"[Init] Workspace ready on branch '{branch}' (Sandbox: {self.flags.sandbox})")

    def build_agent_config(
        self,
        instructions: str = "",
        model: str = "",
        tools: list = None,
        policies: list = None,
    ) -> LocalAgentConfig:
        """Builds LocalAgentConfig mounted to workspace with sandbox policies."""
        active_policies = []
        if self.flags.sandbox:
            active_policies.extend(policy.workspace_only([str(self.workspace)]))
        if policies:
            active_policies.extend(policies)

        return LocalAgentConfig(
            system_instructions=instructions,
            model=model or self.flags.model,
            api_key=self.flags.gemini_api_key or None,
            workspaces=[str(self.workspace)],
            policies=active_policies,
            tools=tools,
            capabilities=CapabilitiesConfig(),
            save_dir=str(self.artifacts_dir),
        )
