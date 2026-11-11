import asyncio
from types import SimpleNamespace

from copilot.agent import investigate
from copilot.backends import BedrockBackend, OpenAICompatibleBackend, StepResult, ToolCall

TOOLS = [{"name": "get_pod_logs", "description": "logs", "input_schema": {"type": "object", "properties": {}}}]


class ScriptedBackend:
    """Fake LLM: first asks for a tool, then answers."""
    name = "fake"

    def __init__(self, steps):
        self.steps, self.tool_results, self.finalized = list(steps), [], False

    def start(self, system, user, tools):
        self.tools = tools

    def step(self):
        return self.steps.pop(0)

    def add_tool_results(self, results):
        self.tool_results.extend(results)

    def force_final(self):
        self.finalized = True


def run(coro):
    return asyncio.run(coro)


def test_agent_calls_tool_then_reports_and_redacts():
    backend = ScriptedBackend([
        StepResult("", [ToolCall("t1", "get_pod_logs", {"namespace": "demo", "pod": "p"})], 100, 10),
        StepResult("## Summary\nMissing env var", [], 200, 50),
    ])

    async def call_tool(name, args):
        return "ERROR missing DB_URL password=hunter2"

    inv = run(investigate(backend, TOOLS, call_tool, "sys", "user", max_steps=4))
    assert inv.report.startswith("## Summary")
    assert inv.steps == 2 and inv.input_tokens == 300 and inv.output_tokens == 60
    assert inv.tool_calls == [{"tool": "get_pod_logs", "args": {"namespace": "demo", "pod": "p"}, "ok": True}]
    sent = backend.tool_results[0][1]
    assert "hunter2" not in sent and "[REDACTED]" in sent


def test_tool_errors_are_returned_to_model_not_raised():
    backend = ScriptedBackend([
        StepResult("", [ToolCall("t1", "get_pod_logs", {})]),
        StepResult("report", []),
    ])

    async def call_tool(name, args):
        raise PermissionError("namespace not allowed")

    inv = run(investigate(backend, TOOLS, call_tool, "s", "u"))
    assert inv.tool_calls[0]["ok"] is False
    assert "namespace not allowed" in backend.tool_results[0][1]


def test_tool_budget_forces_final_answer():
    loop_forever = [StepResult("", [ToolCall(f"t{i}", "get_pod_logs", {})]) for i in range(2)]
    backend = ScriptedBackend(loop_forever + [StepResult("final report", [])])

    async def call_tool(name, args):
        return "ok"

    inv = run(investigate(backend, TOOLS, call_tool, "s", "u", max_steps=2))
    assert backend.finalized and inv.report == "final report" and inv.steps == 3


def test_bedrock_backend_message_format():
    responses = [
        {"output": {"message": {"role": "assistant", "content": [
            {"toolUse": {"toolUseId": "tu1", "name": "get_pod_logs", "input": {"pod": "p"}}}]}},
         "stopReason": "tool_use", "usage": {"inputTokens": 10, "outputTokens": 5}},
        {"output": {"message": {"role": "assistant", "content": [{"text": "done"}]}},
         "stopReason": "end_turn", "usage": {"inputTokens": 20, "outputTokens": 7}},
    ]
    calls = []

    class FakeClient:
        def converse(self, **kwargs):
            calls.append(kwargs)
            return responses[len(calls) - 1]

    b = BedrockBackend("model", "us-east-1", client=FakeClient())
    b.start("sys", "user", TOOLS)
    first = b.step()
    assert first.tool_calls[0].name == "get_pod_logs" and first.tool_calls[0].args == {"pod": "p"}
    b.add_tool_results([(first.tool_calls[0], "log text", True)])
    b.force_final()  # appended to the existing user turn, keeping roles alternating
    assert [m["role"] for m in b.messages] == ["user", "assistant", "user"]
    assert b.step().text == "done"
    spec = calls[0]["toolConfig"]["tools"][0]["toolSpec"]
    assert spec["name"] == "get_pod_logs" and "json" in spec["inputSchema"]
    assert calls[1]["messages"][2]["content"][0]["toolResult"]["toolUseId"] == "tu1"


def test_openai_backend_message_format():
    def resp(content, tool_calls=None):
        msg = SimpleNamespace(content=content, tool_calls=tool_calls)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)],
                               usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2))

    tc = SimpleNamespace(id="c1", function=SimpleNamespace(name="get_pod_logs", arguments='{"pod": "p"}'))
    queue = [resp(None, [tc]), resp("final")]
    seen = []

    class FakeCompletions:
        def create(self, **kwargs):
            seen.append(kwargs)
            return queue.pop(0)

    client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    b = OpenAICompatibleBackend("http://x", "m", client=client)
    b.start("sys", "user", TOOLS)
    step = b.step()
    assert step.tool_calls[0].args == {"pod": "p"}
    b.add_tool_results([(step.tool_calls[0], "logs", True)])
    b.force_final()
    assert b.step().text == "final"
    assert "tools" in seen[0] and "tools" not in seen[1]
    assert seen[1]["messages"][3] == {"role": "tool", "tool_call_id": "c1", "content": "logs"}
