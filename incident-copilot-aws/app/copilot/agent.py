"""The agent loop: ask the LLM, run the tools it requests (via MCP), feed results back, repeat."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from .metrics import REDACTIONS, TOOL_CALLS
from .redact import redact

MAX_TOOL_OUTPUT_CHARS = 6000

ToolCaller = Callable[[str, dict], Awaitable[str]]


@dataclass
class Investigation:
    report: str
    tool_calls: list[dict] = field(default_factory=list)
    steps: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0


async def investigate(backend, tools: list[dict], call_tool: ToolCaller, system: str, user: str,
                      max_steps: int = 6) -> Investigation:
    started = time.perf_counter()
    backend.start(system, user, tools)
    inv = Investigation(report="")

    for step_no in range(max_steps + 1):
        if step_no == max_steps:
            backend.force_final()
        result = await asyncio.to_thread(backend.step)
        inv.steps += 1
        inv.input_tokens += result.input_tokens
        inv.output_tokens += result.output_tokens

        if not result.tool_calls or step_no == max_steps:
            inv.report = result.text.strip() or "The model returned no report."
            break

        outputs = []
        for tc in result.tool_calls:
            try:
                raw = await call_tool(tc.name, tc.args)
                ok = True
            except Exception as exc:  # tool errors go back to the model, they don't crash the run
                raw, ok = f"Tool error: {exc}", False
            clean, kinds = redact(raw)
            for kind in kinds:
                REDACTIONS.labels(kind).inc()
            if len(clean) > MAX_TOOL_OUTPUT_CHARS:
                clean = clean[:MAX_TOOL_OUTPUT_CHARS] + "\n...[truncated]"
            TOOL_CALLS.labels(tc.name, "ok" if ok else "error").inc()
            inv.tool_calls.append({"tool": tc.name, "args": tc.args, "ok": ok})
            outputs.append((tc, clean, ok))
        backend.add_tool_results(outputs)

    inv.seconds = round(time.perf_counter() - started, 2)
    return inv
