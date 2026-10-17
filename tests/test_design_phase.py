from pathlib import Path
from types import SimpleNamespace

from google.antigravity import BuiltinTools

from config.settings import StartupFlags
from src import design_phase
from src.orchestrator import Orchestrator


class FakeEnvironment:
    def __init__(self, workspace: Path):
        self.workspace_path = workspace
        self.capabilities = []

    def build_sandbox_config(self, *, instructions, capabilities):
        self.capabilities.append(capabilities)
        return instructions


def fake_agents(monkeypatch, replies):
    messages = {"generator": [], "reviewer": []}

    class FakeAgent:
        def __init__(self, instructions):
            self.role = "generator" if "Design Document Generator" in instructions else "reviewer"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def chat(self, message):
            messages[self.role].append(message)

            async def chunks():
                yield replies[self.role].pop(0)

            return chunks()

    monkeypatch.setattr(design_phase, "Agent", FakeAgent)
    return messages


def make_orchestrator(tmp_path):
    flags = StartupFlags(workspace_dir=str(tmp_path), artifacts_dir=str(tmp_path / "artifacts"))
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.design_handler = design_phase.DesignPhase(flags, FakeEnvironment(tmp_path))
    return orchestrator


def test_design_revises_until_approved(tmp_path, monkeypatch):
    messages = fake_agents(
        monkeypatch,
        {
            "generator": ["# Design: first draft", "# Design: revised draft"],
            "reviewer": ["REVISE\n- [ ] Cover the failure case.", "APPROVED\n- [x] Coverage is complete."],
        },
    )
    flags = StartupFlags(workspace_dir=str(tmp_path), artifacts_dir=str(tmp_path / "artifacts"))
    env = FakeEnvironment(tmp_path)

    design, review = design_phase.DesignPhase(flags, env).generate("The feature must handle failures.")

    assert design == "# Design: revised draft"
    assert review.startswith("APPROVED")
    assert (tmp_path / "artifacts" / "design.md").read_text() == design + "\n"
    review_log = (tmp_path / "artifacts" / "design_review.md").read_text()
    assert "## Review 1\nREVISE" in review_log
    assert "## Review 2\nAPPROVED" in review_log
    assert "Cover the failure case" in messages["generator"][1]
    assert "Design:\n# Design: first draft" in messages["reviewer"][0]
    assert len(env.capabilities) == 2
    assert all(BuiltinTools.RUN_COMMAND in config.enabled_tools for config in env.capabilities)
    assert all(BuiltinTools.SEARCH_WEB not in config.enabled_tools for config in env.capabilities)
    assert all(BuiltinTools.READ_URL_CONTENT in config.enabled_tools for config in env.capabilities)
    assert all(BuiltinTools.EDIT_FILE not in config.enabled_tools for config in env.capabilities)
    assert all(BuiltinTools.VIEW_FILE not in config.enabled_tools for config in env.capabilities)
    assert all(not config.enable_subagents for config in env.capabilities)


def test_design_is_best_effort_after_six_rejections(tmp_path, monkeypatch):
    messages = fake_agents(
        monkeypatch,
        {
            "generator": [f"# Design: draft {number}" for number in range(1, 7)],
            "reviewer": ["REVISE\n- [ ] Still missing a requirement."] * 6,
        },
    )
    flags = StartupFlags(workspace_dir=str(tmp_path), artifacts_dir=str(tmp_path / "artifacts"))

    design, review = design_phase.DesignPhase(flags, FakeEnvironment(tmp_path)).generate("A requirement")

    assert design == "# Design: draft 6"
    assert review.startswith("REVISE")
    assert len(messages["generator"]) == 6
    assert len(messages["reviewer"]) == 6


def test_human_feedback_reworks_previous_draft(tmp_path, monkeypatch):
    answers = iter(["Add the offline case", "LGTM"])
    monkeypatch.setattr(design_phase.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    messages = fake_agents(
        monkeypatch,
        {
            "generator": ["# Design: first draft", "# Design: offline revision"],
            "reviewer": ["APPROVED", "APPROVED"],
        },
    )

    design = make_orchestrator(tmp_path).design_phase("An offline feature")

    assert design == "# Design: offline revision"
    assert "Previous design:\n# Design: first draft" in messages["generator"][1]
    assert "Latest reviewer feedback:\nAPPROVED" in messages["generator"][1]
    assert "User feedback:\nAdd the offline case" in messages["generator"][1]
    review_log = (tmp_path / "artifacts" / "design_review.md").read_text()
    assert "## Human feedback\nAdd the offline case" in review_log
    assert "## Human approval\nLGTM" in review_log


def test_noninteractive_design_waits_for_human_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(design_phase.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    fake_agents(monkeypatch, {"generator": ["# Design: draft"], "reviewer": ["APPROVED"]})

    assert make_orchestrator(tmp_path).design_phase("A feature") is None
    assert (tmp_path / "artifacts" / "design.md").read_text() == "# Design: draft\n"


def test_orchestrator_waits_before_coding_without_human_approval(tmp_path):
    flags = StartupFlags(workspace_dir=str(tmp_path), artifacts_dir=str(tmp_path / "artifacts"))
    orchestrator = Orchestrator(flags)
    reached = []
    orchestrator.understanding_phase = lambda _: "requirements"
    orchestrator.init_phase = lambda: reached.append("init")
    orchestrator.design_phase = lambda _: None
    orchestrator.coding_phase = lambda: reached.append("coding")

    orchestrator.run("feature")

    assert reached == ["init"]
