import asyncio

from google.antigravity.types import ToolCall, ToolResult
from rich.console import Console

from src.agent_output import _safe_preview, collect_response, tool_result_hook


def test_tool_log_shows_arguments_and_result_without_secret():
    output = []
    console = Console(file=type("Sink", (), {"write": lambda self, value: output.append(value), "flush": lambda self: None})(), force_terminal=False)

    class FakeAgent:
        async def chat(self, _message):
            async def chunks():
                yield ToolCall(name="run_python_checks", args={"source_paths": ["feature.py"], "api_key": "example-secret"})
                yield "done"

            return chunks()

    assert asyncio.run(collect_response(FakeAgent(), "go", "Coding", console)) == "done"
    hook = tool_result_hook("Coding", console)
    asyncio.run(hook.run(None, ToolResult(name="run_python_checks", result={"passed": True, "output": "1 passed"})))
    log = "".join(output)
    assert '"source_paths": ["feature.py"]' in log
    assert "[REDACTED]" in log
    assert "example-secret" not in log
    assert '"passed": true' in log


def test_tool_preview_limits_size_and_redacts_tokens():
    preview = _safe_preview({"output": "AQ." + "a" * 30, "file": "x" * 200}, limit=80)
    assert "AQ." not in preview
    assert "[REDACTED]" in preview
    assert "chars total" in preview
