from pathlib import Path
from urllib.parse import urlsplit
from config.settings import StartupFlags
from google.antigravity import BuiltinTools, LocalAgentConfig, CapabilitiesConfig, CompactionConfig
from google.antigravity.hooks import policy
from google.antigravity.types import RunCommandConfig
from rich.console import Console

from src.agent_output import tool_result_hook


def _wikipedia_url_only(args: dict) -> bool:
    url = args.get("Url") or args.get("url")
    if not isinstance(url, str):
        return False
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        return (
            parsed.scheme == "https"
            and parsed.port is None
            and not parsed.username
            and not parsed.password
            and (host == "wikipedia.org" or host.endswith(".wikipedia.org"))
        )
    except ValueError:
        return False


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
        tool_log_phase: str = "Agent",
    ) -> LocalAgentConfig:
        """Configures sandbox mounting for the target workspace and intermediate artifacts."""
        active_policies = []
        if self.flags.sandbox:
            active_policies.extend(policy.workspace_only([str(self.workspace_path)]))
            active_policies.extend([
                policy.deny(
                    BuiltinTools.READ_URL_CONTENT.value,
                    when=lambda args: not _wikipedia_url_only(args),
                    reason="Only HTTPS Wikipedia URLs are allowed.",
                ),
                policy.allow(BuiltinTools.READ_URL_CONTENT.value),
                policy.deny(BuiltinTools.SEARCH_WEB.value),
                policy.allow(BuiltinTools.RUN_COMMAND.value),
                policy.allow_all(),
            ])
        if policies:
            active_policies.extend(policies)

        return LocalAgentConfig(
            system_instructions=instructions,
            model=model or self.flags.model,
            api_key=self.flags.gemini_api_key or None,
            workspaces=[str(self.workspace_path)],
            policies=active_policies,
            tools=tools,
            hooks=[tool_result_hook(tool_log_phase, Console())],
            capabilities=(capabilities or CapabilitiesConfig()).model_copy(
                update={"run_command_config": RunCommandConfig(enable_sandbox=self.flags.sandbox, timeout_seconds=60)}
            ),
            compaction_config=CompactionConfig(token_threshold=self.flags.compaction_threshold),
            save_dir=str(self.artifacts_path),
        )

    def print_status(self) -> None:
        print(f"[Init] Workspace (Mounted): {self.workspace_path}")
        print(f"[Init] Artifacts Directory: {self.artifacts_path}")
        print(f"[Init] Sandbox Isolation: {'RESTRICTED' if self.flags.sandbox else 'HOST'}")
