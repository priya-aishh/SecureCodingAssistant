import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class StartupFlags:
    """Startup flags loaded from .env and CLI."""
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    model: str = os.getenv("MODEL", "gemini-2.5-flash")
    sandbox: bool = os.getenv("SANDBOX", "true").lower() in ("true", "1")
    workspace_dir: str = os.getenv("WORKSPACE_DIR", ".")
    artifacts_dir: str = os.getenv("ARTIFACTS_DIR", "/tmp/artifacts")
    app_data_dir: str = os.getenv("APP_DATA_DIR", os.path.expanduser("~/.gemini/antigravity"))
    verbose: bool = False
