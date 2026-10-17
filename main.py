import argparse
import sys
from config.settings import StartupFlags
from src.orchestrator import Orchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="Antigravity Coding Assistant")
    parser.add_argument("-p", "--prompt", type=str, help="Task description")
    parser.add_argument("-m", "--model", type=str, default="gemini-2.5-flash", help="Model override")
    parser.add_argument("--api-key", type=str, default="", help="API key override")
    parser.add_argument("--workspace", "--project-dir", dest="workspace_dir", default=".", help="Target workspace directory")
    parser.add_argument("--artifacts-dir", default="/tmp/artifacts", help="Intermediate artifacts directory")
    parser.add_argument("--no-sandbox", dest="sandbox", action="store_false", help="Disable sandbox")
    args = parser.parse_args()

    flags = StartupFlags(
        workspace_dir=args.workspace_dir,
        artifacts_dir=args.artifacts_dir,
        model=args.model,
        gemini_api_key=args.api_key,
        sandbox=args.sandbox,
    )

    task = args.prompt or (input("Task: ").strip() if sys.stdin.isatty() else sys.stdin.read().strip())
    if not task:
        print("No task provided.")
        return

    orchestrator = Orchestrator(flags)
    orchestrator.run(task)


if __name__ == "__main__":
    main()
