"""Simple host-side validation tools for the future coding agent."""

import os
import subprocess
import sys
from pathlib import Path


class CodingTools:
    """Check the workspace and run Python checks on agent-selected paths."""

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).resolve()
        self.last_python_result: dict | None = None
        self.last_validation_snapshot: dict | None = None
        if not self.workspace.is_dir():
            raise ValueError(f"Workspace is not a directory: {self.workspace}")

    def agent_tools(self) -> list:
        """Return these methods for an Antigravity agent config."""
        return [self.check_workspace, self.run_python_checks]

    def workspace_snapshot(self) -> dict:
        """Capture file names, sizes, and modification times for change checks."""
        snapshot = {}
        for directory, subdirs, files in os.walk(self.workspace):
            subdirs[:] = [name for name in subdirs if name not in {".git", ".venv", "venv", "env", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}]
            for name in files:
                path = Path(directory) / name
                try:
                    stat = path.stat()
                    snapshot[path.relative_to(self.workspace).as_posix()] = (stat.st_size, stat.st_mtime_ns)
                except OSError:
                    continue
        return snapshot

    def check_workspace(self) -> dict:
        """Report whether the workspace has files and any uncommitted Git changes."""
        file_count = len(self.workspace_snapshot())
        try:
            git = subprocess.run(
                ["git", "status", "--porcelain=v1", "--untracked-files=all", "--", "."],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            changes = git.stdout.splitlines() if git.returncode == 0 else []
            git_available = git.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            changes = []
            git_available = False
        return {"is_empty": file_count == 0, "file_count": file_count, "git_available": git_available, "git_changes": changes[:50]}

    def changed_files(self, artifacts_dir: Path | None = None) -> list[str]:
        """List all tracked edits and new files on the task branch."""
        has_head = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=self.workspace, capture_output=True
        ).returncode == 0
        commands = (["git", "diff", "HEAD" if has_head else "--cached", "--name-only", "-z"],
                    ["git", "ls-files", "--others", "--exclude-standard", "-z"])
        files = set()
        for command in commands:
            result = subprocess.run(command, cwd=self.workspace, capture_output=True, check=True)
            files.update(path.decode("utf-8") for path in result.stdout.split(b"\0") if path)
        return sorted(
            path for path in files
            if "__pycache__" not in Path(path).parts
            and Path(path).suffix not in {".pyc", ".pyo"}
            and not (self.workspace / path).resolve().is_relative_to(self.workspace / ".venv")
            and not (artifacts_dir and (self.workspace / path).resolve().is_relative_to(artifacts_dir.resolve()))
        )

    def _paths(self, names: list[str]) -> list[str]:
        paths = []
        for name in names:
            path = (self.workspace / name).resolve()
            if (
                not path.is_relative_to(self.workspace)
                or not path.exists()
                or (not path.is_file() and not path.is_dir())
                or (path.is_file() and path.suffix != ".py")
            ):
                raise ValueError(f"Path must exist inside the workspace: {name}")
            paths.append(str(path))
        return paths

    def run_python_checks(self, source_paths: list[str], test_paths: list[str]) -> dict:
        """Compile source paths and run pytest on test paths inside the workspace."""
        sources = self._paths(source_paths)
        tests = self._paths(test_paths)
        if not sources and not tests:
            self.last_python_result = {"passed": False, "tests_run": False, "checks": [], "message": "Provide source_paths or test_paths."}
            return self.last_python_result

        python = self.workspace / ".venv" / "bin" / "python"
        executable = str(python) if python.is_file() else sys.executable
        commands = [("compile", [executable, "-m", "compileall", "-q", *dict.fromkeys(sources + tests)])]
        if tests:
            commands.append(("unit tests", [executable, "-m", "pytest", "-q", *tests]))

        checks = []
        for kind, command in commands:
            try:
                result = subprocess.run(
                    command,
                    cwd=self.workspace,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    check=False,
                )
                checks.append({
                    "kind": kind,
                    "command": command,
                    "passed": result.returncode == 0,
                    "exit_code": result.returncode,
                    "output": (result.stdout + result.stderr)[-8000:],
                })
            except (FileNotFoundError, subprocess.TimeoutExpired) as error:
                checks.append({"kind": kind, "command": command, "passed": False, "error": str(error)})
        self.last_python_result = {
            "passed": bool(tests) and all(check["passed"] for check in checks),
            "tests_run": bool(tests),
            "source_paths": source_paths,
            "test_paths": test_paths,
            "checks": checks,
        }
        self.last_validation_snapshot = self.workspace_snapshot()
        return self.last_python_result
