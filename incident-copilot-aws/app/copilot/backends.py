"""LLM backends with tool calling: Amazon Bedrock (Converse API) and OpenAI-compatible servers (vLLM, Ollama).

Each backend keeps the conversation in its own message format. The agent only sees StepResult/ToolCall.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from .metrics import LLM_ERRORS, LLM_LATENCY, LLM_TOKENS

FINAL_NUDGE = "You have used your tool budget. Do not call more tools. Write the final incident report now."


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class StepResult:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


def _record(provider: str, start: float, step: StepResult) -> None:
    LLM_LATENCY.labels(provider).observe(time.perf_counter() - start)
    LLM_TOKENS.labels(provider, "input").inc(step.input_tokens)
    LLM_TOKENS.labels(provider, "output").inc(step.output_tokens)


class BedrockBackend:
    name = "bedrock"

    def __init__(self, model_id: str, region: str, client=None):
        if client is None:
            import boto3

            client = boto3.client("bedrock-runtime", region_name=region)
        self.client, self.model_id = client, model_id

    def start(self, system: str, user: str, tools: list[dict]) -> None:
        self.system = [{"text": system}]
        self.messages: list[dict] = [{"role": "user", "content": [{"text": user}]}]
        self.tool_config = {
            "tools": [
                {"toolSpec": {"name": t["name"], "description": t["description"] or t["name"],
                              "inputSchema": {"json": t["input_schema"]}}}
                for t in tools
            ]
        }

    def step(self) -> StepResult:
        start = time.perf_counter()
        try:
            resp = self.client.converse(
                modelId=self.model_id,
                system=self.system,
                messages=self.messages,
                toolConfig=self.tool_config,
                inferenceConfig={"maxTokens": 1500, "temperature": 0.1},
            )
        except Exception:
            LLM_ERRORS.labels(self.name).inc()
            raise
        message = resp["output"]["message"]
        self.messages.append(message)
        texts, calls = [], []
        for block in message.get("content", []):
            if "text" in block:
                texts.append(block["text"])
            elif "toolUse" in block:
                tu = block["toolUse"]
                calls.append(ToolCall(tu["toolUseId"], tu["name"], tu.get("input") or {}))
        usage = resp.get("usage", {})
        result = StepResult("\n".join(texts), calls, usage.get("inputTokens", 0), usage.get("outputTokens", 0))
        _record(self.name, start, result)
        return result

    def add_tool_results(self, results: list[tuple[ToolCall, str, bool]]) -> None:
        self.messages.append({
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": tc.id, "content": [{"text": out}], "status": "success" if ok else "error"}}
                for tc, out, ok in results
            ],
        })

    def force_final(self) -> None:
        # Bedrock needs alternating roles, so add the nudge to the last user turn when there is one.
        if self.messages and self.messages[-1]["role"] == "user":
            self.messages[-1]["content"].append({"text": FINAL_NUDGE})
        else:
            self.messages.append({"role": "user", "content": [{"text": FINAL_NUDGE}]})


class OpenAICompatibleBackend:
    """Works with vLLM (--enable-auto-tool-choice) and Ollama, which both expose the OpenAI API."""

    name = "openai"

    def __init__(self, base_url: str, model: str, client=None):
        if client is None:
            from openai import OpenAI

            client = OpenAI(base_url=base_url, api_key="not-needed")
        self.client, self.model = client, model
        self.final = False

    def start(self, system: str, user: str, tools: list[dict]) -> None:
        self.messages: list[dict] = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        self.tools = [
            {"type": "function", "function": {"name": t["name"], "description": t["description"],
                                              "parameters": t["input_schema"]}}
            for t in tools
        ]
        self.final = False

    def step(self) -> StepResult:
        start = time.perf_counter()
        kwargs = {"model": self.model, "messages": self.messages, "temperature": 0.1, "max_tokens": 1500}
        if not self.final:
            kwargs["tools"] = self.tools
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except Exception:
            LLM_ERRORS.labels(self.name).inc()
            raise
        msg = resp.choices[0].message
        entry: dict = {"role": "assistant", "content": msg.content or ""}
        calls = []
        if msg.tool_calls:
            entry["tool_calls"] = [
                {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in msg.tool_calls
            ]
            for c in msg.tool_calls:
                try:
                    args = json.loads(c.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                calls.append(ToolCall(c.id, c.function.name, args))
        self.messages.append(entry)
        usage = resp.usage
        result = StepResult(msg.content or "", calls,
                            usage.prompt_tokens if usage else 0, usage.completion_tokens if usage else 0)
        _record(self.name, start, result)
        return result

    def add_tool_results(self, results: list[tuple[ToolCall, str, bool]]) -> None:
        for tc, out, _ok in results:
            self.messages.append({"role": "tool", "tool_call_id": tc.id, "content": out})

    def force_final(self) -> None:
        self.final = True
        self.messages.append({"role": "user", "content": FINAL_NUDGE})


def make_backend(settings):
    if settings.llm_provider == "bedrock":
        return BedrockBackend(settings.bedrock_model_id, settings.aws_region)
    return OpenAICompatibleBackend(settings.openai_base_url, settings.openai_model)
