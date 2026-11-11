"""Simple, transparent guardrails: input checks, prompt-injection detection and secret redaction.

These are deliberately rule-based so their behaviour is easy to test and explain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|prompts?)",
    r"disregard (the |all )?(system|previous) (prompt|instructions)",
    r"(reveal|show|print) (me )?(your|the) (system prompt|instructions)",
    r"you are now (?!able)",
    r"\bdeveloper mode\b",
    r"\bjailbreak\b",
]
_INJECTION = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "bearer_token": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]{20,}=*"),
    "connection_string_password": re.compile(r"(?i)(password|pwd)\s*[=:]\s*[^\s;'\"]+"),
    "azure_storage_key": re.compile(r"(?i)AccountKey=[A-Za-z0-9+/=]{40,}"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
}


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str = ""


def check_question(question: str, max_chars: int = 1000) -> GuardrailResult:
    q = (question or "").strip()
    if not q:
        return GuardrailResult(False, "empty")
    if len(q) > max_chars:
        return GuardrailResult(False, "too_long")
    if _INJECTION.search(q):
        return GuardrailResult(False, "prompt_injection")
    return GuardrailResult(True)


def redact(text: str) -> tuple[str, list[str]]:
    """Replace secrets with placeholders. Returns (clean_text, kinds_found)."""
    found: list[str] = []
    for kind, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            found.append(kind)
            if kind == "connection_string_password":
                text = pattern.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
            else:
                text = pattern.sub(f"[REDACTED_{kind.upper()}]", text)
    return text, found
