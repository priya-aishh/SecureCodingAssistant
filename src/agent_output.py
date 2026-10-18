"""Show agent activity while collecting its final response."""

import asyncio
import json
import re
from contextlib import suppress
from time import monotonic

from google.antigravity.types import Text as AgentText, ToolCall, ToolResult
from google.antigravity.hooks import post_tool_call
from rich.console import Console
from rich.text import Text


SECRET_KEYS = ("key", "token", "secret", "password", "authorization", "credential")
SECRET_VALUE = re.compile(r"\b(?:AQ\.|AIza)[A-Za-z0-9_-]{12,}|\bBearer\s+\S+", re.IGNORECASE)


def _safe_preview(value: object, limit: int = 1200) -> str:
    """Show useful tool details without dumping large files or credentials."""
    def clean(item: object) -> object:
        if isinstance(item, dict):
            return {str(key): "[REDACTED]" if any(word in str(key).lower() for word in SECRET_KEYS) else clean(val)
                    for key, val in item.items()}
        if isinstance(item, (list, tuple)):
            return [clean(val) for val in item]
        if isinstance(item, str):
            return SECRET_VALUE.sub("[REDACTED]", item)
        return item

    rendered = json.dumps(clean(value), ensure_ascii=False, default=str)
    return rendered[:limit] + (f"… ({len(rendered)} chars total)" if len(rendered) > limit else "")


def tool_result_hook(phase: str, console: Console):
    @post_tool_call
    def log_result(result: ToolResult) -> None:
        name = getattr(result.name, "value", result.name)
        status = "FAILED" if result.error else "finished"
        detail = result.error if result.error else result.result
        console.print(Text(f"[{phase}] Tool {name} {status}; response: {_safe_preview(detail)}", style="dim"))

    return log_result


async def collect_response(agent, message: str, phase: str, console: Console | None = None) -> str:
    console = console or Console()
    started = monotonic()

    async def heartbeat() -> None:
        while True:
            await asyncio.sleep(15)
            elapsed = int(monotonic() - started)
            console.print(Text(f"[{phase}] Still working ({elapsed}s)...", style="dim"))

    progress = asyncio.create_task(heartbeat())
    parts = []
    try:
        response = await agent.chat(message)
        stream = getattr(response, "chunks", response)
        async for chunk in stream:
            if isinstance(chunk, str):
                parts.append(chunk)
            elif isinstance(chunk, AgentText):
                parts.append(chunk.text)
            elif isinstance(chunk, ToolCall):
                name = getattr(chunk.name, "value", chunk.name)
                console.print(Text(f"[{phase}] Tool {name} called with {_safe_preview(chunk.args)}", style="dim"))
            elif isinstance(chunk, ToolResult):
                name = getattr(chunk.name, "value", chunk.name)
                status = "FAILED" if chunk.error else "finished"
                console.print(Text(f"[{phase}] Tool {name} {status}; response: {_safe_preview(chunk.error or chunk.result)}", style="dim"))
        return "".join(parts).strip()
    finally:
        progress.cancel()
        with suppress(asyncio.CancelledError):
            await progress
