"""Remove secrets from logs and tool output before anything is sent to the LLM."""

from __future__ import annotations

import re

PATTERNS: dict[str, re.Pattern[str]] = {
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    "aws_secret_key": re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*[A-Za-z0-9/+=]{40}"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "bearer_token": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]{20,}=*"),
    "password": re.compile(r"(?i)\b(password|passwd|pwd|secret)\s*[=:]\s*[^\s,;'\"]+"),
}


def redact(text: str) -> tuple[str, list[str]]:
    found: list[str] = []
    for kind, pattern in PATTERNS.items():
        if pattern.search(text):
            found.append(kind)
            if kind == "password":
                text = pattern.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
            else:
                text = pattern.sub(f"[REDACTED_{kind.upper()}]", text)
    return text, found
