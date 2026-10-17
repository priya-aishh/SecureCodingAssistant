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
    project_dir: str = os.getenv("PROJECT_DIR", "./workspace")
    verbose: bool = False
