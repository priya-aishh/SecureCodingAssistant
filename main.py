import argparse
import sys
from config.settings import StartupFlags
from src.orchestrator import Orchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="Antigravity Coding Assistant")
    parser.add_argument("-p", "--prompt", type=str, help="Task description")
    parser.add_argument("-m", "--model", type=str, help="Model override")
    parser.add_argument("--api-key", type=str, help="API key override")
    parser.add_argument("--workspace", "--project-dir", dest="workspace_dir", type=str, help="Target workspace directory")
    parser.add_argument("--artifacts-dir", type=str, help="Artifacts directory (default: /tmp/artifacts)")
    parser.add_argument("--no-sandbox", dest="sandbox", action="store_false", help="Disable sandbox")
    args = parser.parse_args()

    flags = StartupFlags()

    if args.model:
        flags.model = args.model
    if args.api_key:
        flags.gemini_api_key = args.api_key
    if args.workspace_dir:
        flags.workspace_dir = args.workspace_dir
    if args.artifacts_dir:
        flags.artifacts_dir = args.artifacts_dir
    if args.sandbox is False:
        flags.sandbox = False

    task = args.prompt or (input("Task: ").strip() if sys.stdin.isatty() else sys.stdin.read().strip())
    if not task:
        print("No task provided.")
        return

    orchestrator = Orchestrator(flags)
    orchestrator.run(task)


if __name__ == "__main__":
    main()
