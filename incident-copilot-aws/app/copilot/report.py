"""Turn an investigation into a stored incident record and a Slack message."""

from __future__ import annotations

from datetime import datetime, timezone

from .agent import Investigation
from .alerts import Alert


def build_incident(alert: Alert, inv: Investigation, provider: str) -> dict:
    return {
        "id": f"{alert.fingerprint}-{int(datetime.now(timezone.utc).timestamp())}",
        "alert": alert.name,
        "severity": alert.severity,
        "namespace": alert.namespace,
        "labels": alert.labels,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "report": inv.report,
        "tools_used": [t["tool"] for t in inv.tool_calls],
        "steps": inv.steps,
        "tokens": inv.input_tokens + inv.output_tokens,
        "seconds": inv.seconds,
        "provider": provider,
    }


def slack_text(incident: dict) -> str:
    header = f":rotating_light: *{incident['alert']}* ({incident['severity']}) in `{incident['namespace'] or 'cluster'}`"
    footer = (f"_tools: {', '.join(incident['tools_used']) or 'none'} · {incident['seconds']}s · "
              f"{incident['tokens']} tokens · {incident['provider']}_")
    return f"{header}\n{incident['report']}\n{footer}"
