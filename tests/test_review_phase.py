import subprocess
from types import SimpleNamespace

from config.settings import StartupFlags
from src import review_phase
from src.orchestrator import Orchestrator


class FakeEnvironment:
    def __init__(self):
        self.config_args = None

    def build_sandbox_config(self, **kwargs):
        self.config_args = kwargs
        return SimpleNamespace(**kwargs)


def test_code_reviewer_sees_requirements_design_diff_and_validation(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "feature.py").write_text("VALUE = 1\n", encoding="utf-8")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "coding_validation.json").write_text('{"passed": true}', encoding="utf-8")
    messages = []

    class FakeAgent:
        def __init__(self, _):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def chat(self, message):
            messages.append(message)

            async def chunks():
                yield "REVISE\n- Fix feature.py"

            return chunks()

    monkeypatch.setattr(review_phase, "Agent", FakeAgent)
    flags = StartupFlags(workspace_dir=str(tmp_path), artifacts_dir=str(artifacts))
    env = FakeEnvironment()

    result = review_phase.ReviewPhase(flags, env).run("Requirement", "Approved design", "Coding summary")

    assert result.startswith("REVISE")
    assert "User requirements:\nRequirement" in messages[0]
    assert "Human-approved design:\nApproved design" in messages[0]
    assert "+VALUE = 1" in messages[0]
    assert '"passed": true' in messages[0]
    assert (artifacts / "coding_diff.patch").exists()
    assert "Fix feature.py" in (artifacts / "coding_review.md").read_text()
    assert review_phase.BuiltinTools.EDIT_FILE not in env.config_args["capabilities"].enabled_tools


def test_review_feedback_returns_to_coding_before_commit(tmp_path):
    flags = StartupFlags(workspace_dir=str(tmp_path), artifacts_dir=str(tmp_path / "artifacts"))
    orchestrator = Orchestrator(flags)
    coding_calls = []
    commits = []
    reviews = iter(["REVISE\n- Fix the boundary case", "APPROVED"])
    orchestrator.understanding_phase = lambda _: "requirements"
    orchestrator.init_phase = lambda: None
    orchestrator.design_phase = lambda _: "approved design"
    orchestrator.coding_phase = lambda requirements, design, feedback: coding_calls.append(feedback) or "summary"
    orchestrator.review_phase = lambda requirements, design, summary: next(reviews)
    orchestrator.commit_phase = lambda: commits.append(True)

    orchestrator.run("feature")

    assert coding_calls == ["", "REVISE\n- Fix the boundary case"]
    assert commits == [True]
