import argparse
import os
import sys
from dotenv import load_dotenv
from config.settings import StartupFlags
from src.orchestrator import Orchestrator


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Antigravity Coding Assistant")
    parser.add_argument("-p", "--prompt", type=str, help="Task description")
    parser.add_argument("-m", "--model", type=str, default=os.getenv("MODEL", StartupFlags.model), help="Model override")
    parser.add_argument("--design-model", default=os.getenv("DESIGN_MODEL", StartupFlags.design_model), help="Design generator model")
    parser.add_argument("--api-key", type=str, default=os.getenv("GEMINI_API_KEY", ""), help="API key override")
    parser.add_argument("--workspace", "--project-dir", dest="workspace_dir", default=".", help="Target workspace directory")
    parser.add_argument("--artifacts-dir", default="/tmp/artifacts", help="Intermediate artifacts directory")
    parser.add_argument(
        "--compaction-threshold",
        type=int,
        default=StartupFlags.compaction_threshold,
        help="Token count that triggers agent history compaction (default: 300000)",
    )
    parser.add_argument("--no-sandbox", dest="sandbox", action="store_false", help="Disable sandbox")
    args = parser.parse_args()
    if args.compaction_threshold <= 0:
        parser.error("--compaction-threshold must be a positive integer")

    flags = StartupFlags(
        workspace_dir=args.workspace_dir,
        artifacts_dir=args.artifacts_dir,
        model=args.model,
        design_model=args.design_model,
        gemini_api_key=args.api_key,
        sandbox=args.sandbox,
        compaction_threshold=args.compaction_threshold,
    )

    task = args.prompt or (sys.stdin.read().strip() if not sys.stdin.isatty() else "")
    orchestrator = Orchestrator(flags)
    orchestrator.run(task)


if __name__ == "__main__":
    main()
