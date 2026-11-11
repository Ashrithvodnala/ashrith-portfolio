"""Runtime settings, read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    llm_provider: str            # "azure" (Azure OpenAI) or "local" (any OpenAI-compatible server, e.g. Ollama)
    chat_model: str              # Azure: chat deployment name. Local: model name.
    embedding_model: str         # Azure: embedding deployment name. Local: model name.
    embedding_dim: int
    azure_endpoint: str
    azure_api_version: str
    azure_api_key: str           # optional; empty = use Microsoft Entra ID (workload identity)
    local_base_url: str
    database_url: str
    top_k: int
    max_question_chars: int
    max_distance: float          # cosine distance cut-off: chunks further away are treated as "not relevant"
    admin_token: str             # protects POST /ingest


def load_settings() -> Settings:
    env = os.getenv
    return Settings(
        llm_provider=env("LLM_PROVIDER", "local"),
        chat_model=env("CHAT_MODEL", "llama3.2:3b"),
        embedding_model=env("EMBEDDING_MODEL", "nomic-embed-text"),
        embedding_dim=int(env("EMBEDDING_DIM", "768")),
        azure_endpoint=env("AZURE_OPENAI_ENDPOINT", ""),
        azure_api_version=env("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        azure_api_key=env("AZURE_OPENAI_API_KEY", ""),
        local_base_url=env("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1"),
        database_url=env("DATABASE_URL", "postgresql://opspilot:opspilot@localhost:5432/opspilot"),
        top_k=int(env("TOP_K", "4")),
        max_question_chars=int(env("MAX_QUESTION_CHARS", "1000")),
        max_distance=float(env("MAX_DISTANCE", "0.55")),
        admin_token=env("ADMIN_TOKEN", ""),
    )
