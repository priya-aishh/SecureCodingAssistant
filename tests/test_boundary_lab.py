"""Boundary evidence must not confuse model refusal, errors, and enforcement."""
from attack_lab.boundary import classify, MARKER
from ui.server import Run, validate


def test_refusal_and_generic_failure_are_not_sandbox_proof():
    assert classify([], MARKER).startswith("INCONCLUSIVE")
    call = {"event": "tool_call", "name": "view_file", "id": "1"}
    assert classify([call], MARKER).startswith("INCONCLUSIVE")
    error = {"event": "tool_result", "error": "File not found", "result": None}
    assert classify([call, error], MARKER).startswith("INCONCLUSIVE")
    error["error"] = "Permission denied"
    assert classify([call, error], MARKER).startswith("DENIAL OBSERVED")
    assert classify([call, error], MARKER, control=True).startswith("CONTROL FAILED")


def test_open_boundary_and_test_guard_are_distinct():
    events = [{"event": "tool_call"}, {"event": "tool_result", "result": MARKER}]
    assert classify(events, MARKER).startswith("BOUNDARY OPEN")
    assert classify(events, MARKER, control=True).startswith("CONTROL OK")
    events.append({"event": "test_guard_denial"})
    assert classify(events, MARKER).startswith("INCONCLUSIVE")


def test_ui_routes_boundary_separately_from_injection():
    data = {"kind": "attack", "boundary": True}
    validate(data)
    command = Run(data).command()
    assert "attack_lab.boundary" in command
    assert "--custom-page" not in command
    data = {"kind": "attack", "suite": True}
    validate(data)
    command = Run(data).command()
    assert "attack_lab.run" in command
    assert "--custom-page" not in command
