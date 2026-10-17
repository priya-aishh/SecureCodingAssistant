import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.antigravity import BuiltinTools

from config.settings import StartupFlags
from src import coding_phase
from src.orchestrator import Orchestrator


class FakeEnvironment:
    def __init__(self, workspace: Path):
        self.workspace_path = workspace
        self.config_args = None

    def build_sandbox_config(self, **kwargs):
        self.config_args = kwargs
        return SimpleNamespace(**kwargs)


def test_coding_phase_uses_approved_design_and_validates_changes(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    flags = StartupFlags(workspace_dir=str(tmp_path), artifacts_dir=str(tmp_path / "artifacts"))
    env = FakeEnvironment(tmp_path)
    messages = []

    class FakeAgent:
        def __init__(self, config):
            self.config = config

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def chat(self, message):
            messages.append(message)
            (tmp_path / "feature.py").write_text("def value():\n    return 42\n")
            tests = tmp_path / "tests"
            tests.mkdir()
            (tests / "test_feature.py").write_text("from feature import value\n\ndef test_value():\n    assert value() == 42\n")
            workspace_status, python_checks = self.config.tools
            assert workspace_status()["is_empty"] is False
            assert python_checks(["feature.py"], ["tests"])["passed"] is True

            async def chunks():
                yield "Implemented feature and tested it."

            return chunks()

    monkeypatch.setattr(coding_phase, "Agent", FakeAgent)

    result = coding_phase.CodingPhase(flags, env).run("Return 42", "Implement value()")

    assert result == "Implemented feature and tested it."
    assert "User requirements:\nReturn 42" in messages[0]
    assert "Approved design document:\nImplement value()" in messages[0]
    assert BuiltinTools.EDIT_FILE in env.config_args["capabilities"].enabled_tools
    assert BuiltinTools.CREATE_FILE in env.config_args["capabilities"].enabled_tools
    assert (tmp_path / "artifacts" / "coding_summary.md").read_text() == result + "\n"
    validation = json.loads((tmp_path / "artifacts" / "coding_validation.json").read_text())
    assert validation["python_checks"]["passed"] is True
    assert "tests/test_feature.py" in validation["changed_files"]


def test_coding_phase_rejects_completion_without_changes(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    flags = StartupFlags(workspace_dir=str(tmp_path), artifacts_dir=str(tmp_path / "artifacts"))

    class FakeAgent:
        def __init__(self, _):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def chat(self, _):
            async def chunks():
                yield "Done."

            return chunks()

    monkeypatch.setattr(coding_phase, "Agent", FakeAgent)

    with pytest.raises(RuntimeError, match="without workspace changes"):
        coding_phase.CodingPhase(flags, FakeEnvironment(tmp_path)).run("Requirement", "Design")


def test_coding_phase_rejects_tests_that_skip_changed_test_file(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    flags = StartupFlags(workspace_dir=str(tmp_path), artifacts_dir=str(tmp_path / "artifacts"))

    class FakeAgent:
        def __init__(self, config):
            self.config = config

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def chat(self, _):
            (tmp_path / "feature.py").write_text("VALUE = 1\n")
            tests = tmp_path / "tests"
            tests.mkdir()
            (tests / "test_changed.py").write_text("def test_changed():\n    assert True\n")
            (tests / "test_other.py").write_text("def test_other():\n    assert True\n")
            self.config.tools[1](["feature.py"], ["tests/test_other.py"])

            async def chunks():
                yield "Done."

            return chunks()

    monkeypatch.setattr(coding_phase, "Agent", FakeAgent)

    with pytest.raises(RuntimeError, match="did not include every changed Python file"):
        coding_phase.CodingPhase(flags, FakeEnvironment(tmp_path)).run("Requirement", "Design")


def test_orchestrator_passes_requirements_and_design_to_coding(tmp_path):
    flags = StartupFlags(workspace_dir=str(tmp_path), artifacts_dir=str(tmp_path / "artifacts"))
    orchestrator = Orchestrator(flags)
    calls = []
    orchestrator.understanding_phase = lambda _: "requirements"
    orchestrator.init_phase = lambda: None
    orchestrator.design_phase = lambda _: "approved design"
    orchestrator.coding_phase = lambda requirements, design, feedback: calls.append((requirements, design, feedback))
    orchestrator.review_phase = lambda requirements, design, summary: "APPROVED"
    orchestrator.commit_phase = lambda: None

    orchestrator.run("feature")

    assert calls == [("requirements", "approved design", "")]
