import json
import subprocess
from types import SimpleNamespace

from config.settings import StartupFlags
from src.commit_phase import CommitPhase


def git(workspace, *args):
    return subprocess.run(["git", *args], cwd=workspace, check=True, capture_output=True, text=True).stdout.strip()


def test_commit_stages_only_validated_files(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "user.email", "test@example.com")
    (tmp_path / "README.md").write_text("initial\n")
    git(tmp_path, "add", "README.md")
    git(tmp_path, "commit", "-qm", "initial")
    git(tmp_path, "switch", "-qc", "task-test")
    (tmp_path / "feature.py").write_text("VALUE = 1\n")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "feature.pyc").write_bytes(b"cache")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "coding_validation.json").write_text(json.dumps({
        "changed_files": ["feature.py"], "python_checks": {"passed": True}
    }))

    flags = StartupFlags(workspace_dir=str(tmp_path), artifacts_dir=str(artifacts))
    CommitPhase(flags, SimpleNamespace(branch_name="task-test")).run()

    assert git(tmp_path, "branch", "--show-current") == "main"
    assert git(tmp_path, "ls-files") == "README.md\nfeature.py"
    assert (cache / "feature.pyc").exists()
