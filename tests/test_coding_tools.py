import subprocess

import pytest
from google.antigravity.connections.local.interactions_config_converter import callable_to_function_tool_dict
from google.antigravity.tools.tool_runner import ToolRunner

from src.coding_tools import CodingTools


def test_changed_files_include_earlier_rounds_but_exclude_generated_files(tmp_path):
    import subprocess

    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("initial\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    (tmp_path / "first.py").write_text("FIRST = 1\n")
    (tmp_path / "second.py").write_text("SECOND = 2\n")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "first.pyc").write_bytes(b"cache")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "design.md").write_text("draft\n")

    assert CodingTools(tmp_path).changed_files(artifacts) == ["first.py", "second.py"]


def test_workspace_status_ignores_git_directory_and_reports_changes(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    tools = CodingTools(tmp_path)
    assert tools.check_workspace()["is_empty"] is True

    (tmp_path / "feature.py").write_text("VALUE = 1\n")
    status = tools.check_workspace()
    assert status["is_empty"] is False
    assert status["file_count"] == 1
    assert any("feature.py" in change for change in status["git_changes"])


def test_python_checks_compile_and_run_selected_tests(tmp_path):
    (tmp_path / "feature.py").write_text("VALUE = 1\n")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_feature.py").write_text("def test_feature():\n    assert 1 == 1\n")

    result = CodingTools(tmp_path).run_python_checks(["feature.py"], ["tests/test_feature.py"])

    assert result["passed"] is True
    assert [check["kind"] for check in result["checks"]] == ["compile", "unit tests"]


def test_python_checks_reject_paths_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (tmp_path / "outside.py").write_text("print('outside')\n")

    with pytest.raises(ValueError):
        CodingTools(workspace).run_python_checks(["../outside.py"], [])


def test_compile_only_does_not_claim_full_validation(tmp_path):
    (tmp_path / "feature.py").write_text("VALUE = 1\n")

    result = CodingTools(tmp_path).run_python_checks(["feature.py"], [])

    assert result["checks"][0]["passed"] is True
    assert result["tests_run"] is False
    assert result["passed"] is False


def test_python_checks_report_compile_and_test_failures(tmp_path):
    (tmp_path / "broken.py").write_text("def broken(:\n")
    (tmp_path / "test_failure.py").write_text("def test_failure():\n    assert False\n")

    result = CodingTools(tmp_path).run_python_checks(["broken.py"], ["test_failure.py"])

    assert result["passed"] is False
    assert [check["passed"] for check in result["checks"]] == [False, False]


def test_methods_are_valid_agent_tools(tmp_path):
    methods = CodingTools(tmp_path).agent_tools()
    runner = ToolRunner(methods)
    schemas = [callable_to_function_tool_dict(method, runner) for method in methods]

    assert [schema["name"] for schema in schemas] == ["check_workspace", "run_python_checks"]
    assert schemas[1]["parameters"]["required"] == ["source_paths", "test_paths"]
