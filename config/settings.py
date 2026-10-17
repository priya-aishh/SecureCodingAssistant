from dataclasses import dataclass


@dataclass
class StartupFlags:
    """Startup flags with standard defaults."""
    workspace_dir: str = "."
    artifacts_dir: str = "/tmp/artifacts"
    model: str = "gemini-2.5-flash"
    gemini_api_key: str = ""
    sandbox: bool = True
