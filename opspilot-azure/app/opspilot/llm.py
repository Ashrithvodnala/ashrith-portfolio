"""LLM client: Azure OpenAI in the cloud, or any OpenAI-compatible server (Ollama, vLLM) locally."""

from __future__ import annotations

import time
from dataclasses import dataclass

from openai import AzureOpenAI, OpenAI

from .config import Settings
from .metrics import LLM_ERRORS, LLM_LATENCY, LLM_TOKENS


@dataclass
class ChatResult:
    text: str
    prompt_tokens: int
    completion_tokens: int


def _make_client(s: Settings):
    if s.llm_provider == "azure":
        if s.azure_api_key:
            return AzureOpenAI(azure_endpoint=s.azure_endpoint, api_key=s.azure_api_key, api_version=s.azure_api_version)
        # Keyless: AKS workload identity -> Microsoft Entra ID token ("Cognitive Services OpenAI User" role).
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider

        token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
        return AzureOpenAI(
            azure_endpoint=s.azure_endpoint, azure_ad_token_provider=token_provider, api_version=s.azure_api_version
        )
    return OpenAI(base_url=s.local_base_url, api_key="not-needed-locally")


class LLMClient:
    def __init__(self, settings: Settings):
        self.s = settings
        self.client = _make_client(settings)

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self.s.embedding_model
        start = time.perf_counter()
        try:
            resp = self.client.embeddings.create(model=model, input=texts)
        except Exception:
            LLM_ERRORS.labels("embed", model).inc()
            raise
        finally:
            LLM_LATENCY.labels("embed", model).observe(time.perf_counter() - start)
        if resp.usage:
            LLM_TOKENS.labels(model, "prompt").inc(resp.usage.prompt_tokens)
        return [d.embedding for d in resp.data]

    def chat(self, system: str, user: str) -> ChatResult:
        model = self.s.chat_model
        start = time.perf_counter()
        try:
            resp = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.1,
                max_tokens=600,
            )
        except Exception:
            LLM_ERRORS.labels("chat", model).inc()
            raise
        finally:
            LLM_LATENCY.labels("chat", model).observe(time.perf_counter() - start)
        usage = resp.usage
        pt, ct = (usage.prompt_tokens, usage.completion_tokens) if usage else (0, 0)
        LLM_TOKENS.labels(model, "prompt").inc(pt)
        LLM_TOKENS.labels(model, "completion").inc(ct)
        return ChatResult(resp.choices[0].message.content or "", pt, ct)
