import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load .env file automatically
load_dotenv()


@dataclass
class StartupFlags:
    """Basic startup flags and configuration loaded from .env and CLI."""
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    model: str = os.getenv("MODEL", "gemini-2.5-flash")
    sandbox: bool = os.getenv("SANDBOX", "true").lower() in ("true", "1")
    workspace_dir: str = os.getenv("WORKSPACE_DIR", "./workspace")
    verbose: bool = False
