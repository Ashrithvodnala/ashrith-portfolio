"""Settings from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    llm_provider: str          # "bedrock" | "openai" (any OpenAI-compatible server: vLLM, Ollama)
    bedrock_model_id: str
    aws_region: str
    openai_base_url: str
    openai_model: str
    max_steps: int             # max tool-calling rounds per investigation
    slack_webhook_url: str     # optional: post reports to Slack


def load_settings() -> Settings:
    env = os.getenv
    return Settings(
        llm_provider=env("LLM_PROVIDER", "openai"),
        bedrock_model_id=env("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0"),
        aws_region=env("AWS_REGION", "us-east-1"),
        openai_base_url=env("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        openai_model=env("OPENAI_MODEL", "qwen2.5:3b"),
        max_steps=int(env("MAX_STEPS", "6")),
        slack_webhook_url=env("SLACK_WEBHOOK_URL", ""),
    )
