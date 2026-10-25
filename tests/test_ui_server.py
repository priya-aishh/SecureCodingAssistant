"""Input boundaries and command construction for the local browser console."""

import json
import os
import sys
import threading
import time

import pytest

from ui.server import Run, validate


def test_attack_run_keeps_custom_page_in_mcp_fixture(tmp_path):
    data = {"kind": "attack", "url": "https://en.wikipedia.org/wiki/Sample",
            "article": "Untrusted page text", "question": "Summarize the page", "api_key": "test-secret"}
    validate(data)
    run = Run(data)
    command = run.command()
    assert "--custom-page" in command
    assert (run.root / "article.md").read_text(encoding="utf-8") == "Untrusted page text"
    assert "test-secret" not in command


def test_full_journey_uses_disposable_fixture_directory(tmp_path):
    data = {"kind": "journey", "workspace": str(tmp_path), "task": "Add a feature",
            "url": "https://en.wikipedia.org/wiki/Sample", "article": "Local article"}
    validate(data)
    run = Run(data)
    command = run.command()
    assert "--mock-mode" in command
    assert json.loads((run.root / "pages" / "manifest.json").read_text()) == {
        data["url"]: "article.md"
    }
    assert "Consult this background page" in command[command.index("--prompt") + 1]


def test_ui_rejects_non_wikipedia_and_missing_workspace(tmp_path):
    with pytest.raises(ValueError):
        validate({"kind": "attack", "url": "https://example.com/page",
                  "article": "Test", "question": "What?"})
    with pytest.raises(ValueError):
        validate({"kind": "journey", "workspace": "", "task": "Implement this", "article": "", "url": ""})


def test_pty_run_exposes_design_approval_and_resumes(tmp_path):
    run = Run({"kind": "journey", "workspace": str(tmp_path), "task": "Demo"})
    script = (
        "print('[Understanding] Ready', flush=True);"
        "print('[Design] Type LGTM to approve or describe what to change: ', end='', flush=True);"
        "reply=input();"
        "print('[Coding] Resumed after '+reply, flush=True)"
    )
    run.command = lambda: [sys.executable, "-c", script]
    worker = threading.Thread(target=run.run)
    worker.start()
    deadline = time.monotonic() + 5
    while run.status != "awaiting_approval" and time.monotonic() < deadline:
        time.sleep(0.01)
    assert run.status == "awaiting_approval"
    os.write(run.master, b"LGTM\n")
    worker.join(timeout=5)
    assert not worker.is_alive()
    assert run.status == "completed"
    assert "[Coding] Resumed after LGTM" in "".join(event["text"] for event in run.events)
