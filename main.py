import argparse
import sys
from config.settings import StartupFlags
from src.orchestrator import Orchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="Antigravity Coding Assistant")
    parser.add_argument("-p", "--prompt", type=str, help="Task description")
    parser.add_argument("-m", "--model", type=str, help="Model override")
    parser.add_argument("--api-key", type=str, help="API key override")
    parser.add_argument("--project-dir", "--workspace", dest="project_dir", type=str, help="Project directory to mount")
    parser.add_argument("--no-sandbox", dest="sandbox", action="store_false", help="Disable sandbox")
    args = parser.parse_args()

    # Load defaults from .env
    flags = StartupFlags()

    # Apply terminal overrides
    if args.model:
        flags.model = args.model
    if args.api_key:
        flags.gemini_api_key = args.api_key
    if args.project_dir:
        flags.project_dir = args.project_dir
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
