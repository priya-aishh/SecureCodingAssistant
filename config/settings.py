from dataclasses import dataclass
from pathlib import Path


@dataclass
class StartupFlags:
    """Startup flags with standard defaults."""
    workspace_dir: str = "."
    artifacts_dir: str = "/tmp/artifacts"
    app_data_dir: str = str(Path.home() / ".gemini" / "antigravity")
    model: str = "gemini-2.5-flash"
    gemini_api_key: str = ""
    sandbox: bool = True
    verbose: bool = False
