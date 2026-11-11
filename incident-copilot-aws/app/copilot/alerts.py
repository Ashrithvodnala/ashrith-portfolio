"""Parse Alertmanager webhook payloads and turn an alert into an investigation request."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Alert:
    name: str
    status: str
    severity: str
    namespace: str
    labels: dict = field(default_factory=dict)
    annotations: dict = field(default_factory=dict)
    starts_at: str = ""
    fingerprint: str = ""


def parse_alertmanager(payload: dict) -> list[Alert]:
    """Return firing alerts only. Alertmanager also sends 'resolved' notifications, which we skip."""
    alerts = []
    for a in payload.get("alerts", []):
        if a.get("status") != "firing":
            continue
        labels = a.get("labels", {})
        fp = a.get("fingerprint") or hashlib.sha1(
            "|".join(f"{k}={v}" for k, v in sorted(labels.items())).encode()
        ).hexdigest()[:16]
        alerts.append(
            Alert(
                name=labels.get("alertname", "unknown"),
                status="firing",
                severity=labels.get("severity", "none"),
                namespace=labels.get("namespace", ""),
                labels=labels,
                annotations=a.get("annotations", {}),
                starts_at=a.get("startsAt", ""),
                fingerprint=fp,
            )
        )
    return alerts


SYSTEM_PROMPT = """You are Incident Copilot, an SRE assistant investigating a Kubernetes alert.
Use the available tools to gather evidence: unhealthy pods, pod logs (including the previous crashed container),
events, deployment status and Prometheus metrics. Only use read-only tools. Call at most a few tools.
Then write a short incident report in Markdown with exactly these sections:
## Summary (one sentence)
## Evidence (bullet points quoting the specific log lines, events or metrics you found)
## Likely root cause
## Recommended next steps (concrete kubectl or configuration actions)
## Confidence (low, medium or high, with one reason)
Do not invent evidence. If the tools return nothing useful, say so."""


def build_investigation_prompt(alert: Alert) -> str:
    interesting = {k: v for k, v in alert.labels.items() if k not in {"prometheus", "endpoint", "service", "job"}}
    lines = [
        f"Alert: {alert.name} (severity: {alert.severity})",
        f"Started at: {alert.starts_at or 'unknown'}",
        "Labels: " + ", ".join(f"{k}={v}" for k, v in sorted(interesting.items())),
    ]
    if alert.annotations.get("summary"):
        lines.append(f"Summary: {alert.annotations['summary']}")
    if alert.annotations.get("description"):
        lines.append(f"Description: {alert.annotations['description']}")
    lines.append("Investigate this alert and write the incident report.")
    return "\n".join(lines)
