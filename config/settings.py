from dataclasses import dataclass


@dataclass
class StartupFlags:
    """Startup flags with standard defaults."""
    workspace_dir: str = "."
    artifacts_dir: str = "/tmp/artifacts"
    model: str = "gemini-3.8-flash"
    design_model: str = "gemini-4-argon"
    gemini_api_key: str = ""
    sandbox: bool = True
    compaction_threshold: int = 300_000
