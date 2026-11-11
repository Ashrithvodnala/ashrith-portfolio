"""Starts the real MCP server (stdio) with sample data and runs the agent against it."""

import asyncio

from copilot.agent import investigate
from copilot.backends import StepResult, ToolCall
from copilot.mcp_client import mcp_tools


class TwoStepBackend:
    name = "fake"

    def start(self, system, user, tools):
        self.n = 0

    def step(self):
        self.n += 1
        if self.n == 1:
            return StepResult("", [ToolCall("1", "list_unhealthy_pods", {"namespace": "demo"}),
                                   ToolCall("2", "get_pod_logs", {"namespace": "demo", "pod": "payments-api"})])
        return StepResult("## Summary\nPAYMENTS_DB_URL missing", [])

    def add_tool_results(self, results):
        self.results = results

    def force_final(self):
        pass


def test_agent_uses_real_mcp_server(monkeypatch):
    monkeypatch.setenv("K8S_MODE", "fake")

    async def main():
        async with mcp_tools() as (tools, call_tool):
            names = {t["name"] for t in tools}
            assert {"list_unhealthy_pods", "get_pod_logs", "get_events", "describe_deployment",
                    "query_prometheus"} <= names
            backend = TwoStepBackend()
            inv = await investigate(backend, tools, call_tool, "s", "u")
            return inv, backend

    inv, backend = asyncio.run(main())
    assert inv.report.startswith("## Summary")
    assert all(ok for _, _, ok in backend.results)
    logs = backend.results[1][1]
    assert "PAYMENTS_DB_URL" in logs and "hunter2" not in logs   # secret redacted before reaching the LLM


def test_namespace_allow_list(monkeypatch):
    monkeypatch.setenv("K8S_MODE", "fake")
    monkeypatch.setenv("ALLOWED_NAMESPACES", "demo")

    async def main():
        async with mcp_tools() as (tools, call_tool):
            try:
                await call_tool("get_pod_logs", {"namespace": "kube-system", "pod": "x"})
            except RuntimeError as exc:
                return str(exc)
            return "no error"

    assert "not in ALLOWED_NAMESPACES" in asyncio.run(main())
