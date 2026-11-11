"""FastAPI service: Alertmanager webhook -> AI investigation -> incident report (UI, API, Slack)."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from prometheus_client import make_asgi_app

from .agent import investigate
from .alerts import SYSTEM_PROMPT, build_investigation_prompt, parse_alertmanager
from .backends import make_backend
from .config import load_settings
from .mcp_client import mcp_tools
from .metrics import INVESTIGATION_SECONDS, INVESTIGATIONS
from .report import build_incident, slack_text

settings = load_settings()
app = FastAPI(title="Incident Copilot", version="0.1.0")
app.mount("/metrics", make_asgi_app())

INCIDENTS: "OrderedDict[str, dict]" = OrderedDict()   # newest last; demo storage (in memory)
RECENT: dict[str, float] = {}                         # fingerprint -> last investigation time
DEDUP_SECONDS = 600
_lock = asyncio.Semaphore(2)                          # at most 2 investigations at once


async def _notify(incident: dict) -> None:
    if not settings.slack_webhook_url:
        return
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(settings.slack_webhook_url, json={"text": slack_text(incident)})


async def run_investigation(alert) -> dict:
    async with _lock:
        start = time.perf_counter()
        try:
            async with mcp_tools() as (tools, call_tool):
                backend = make_backend(settings)
                inv = await investigate(backend, tools, call_tool, SYSTEM_PROMPT,
                                        build_investigation_prompt(alert), settings.max_steps)
            incident = build_incident(alert, inv, backend.name)
            INVESTIGATIONS.labels("ok").inc()
        except Exception as exc:
            INVESTIGATIONS.labels("error").inc()
            incident = {"id": f"{alert.fingerprint}-error-{int(time.time())}", "alert": alert.name,
                        "severity": alert.severity, "namespace": alert.namespace, "report": f"Investigation failed: {exc}",
                        "tools_used": [], "steps": 0, "tokens": 0, "seconds": 0, "provider": settings.llm_provider,
                        "labels": alert.labels, "created_at": ""}
        finally:
            INVESTIGATION_SECONDS.observe(time.perf_counter() - start)
        INCIDENTS[incident["id"]] = incident
        while len(INCIDENTS) > 50:
            INCIDENTS.popitem(last=False)
        await _notify(incident)
        return incident


@app.post("/webhook/alertmanager")
async def alertmanager_webhook(request: Request, background: BackgroundTasks):
    payload = await request.json()
    queued = []
    now = time.time()
    for alert in parse_alertmanager(payload):
        if now - RECENT.get(alert.fingerprint, 0) < DEDUP_SECONDS:
            INVESTIGATIONS.labels("skipped").inc()   # same alert investigated recently
            continue
        RECENT[alert.fingerprint] = now
        background.add_task(run_investigation, alert)
        queued.append(alert.name)
    return {"queued": queued}


@app.post("/investigate")
async def investigate_now(request: Request):
    """Synchronous variant for demos: send an Alertmanager-style payload and wait for the report."""
    alerts = parse_alertmanager(await request.json())
    if not alerts:
        raise HTTPException(400, "no firing alerts in payload")
    return await run_investigation(alerts[0])


@app.get("/incidents")
def list_incidents():
    return list(reversed(INCIDENTS.values()))


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    if incident_id not in INCIDENTS:
        raise HTTPException(404, "not found")
    return INCIDENTS[incident_id]


@app.get("/healthz")
def healthz():
    return {"status": "ok", "provider": settings.llm_provider}


@app.get("/", response_class=HTMLResponse)
def ui():
    return (Path(__file__).parent / "ui.html").read_text(encoding="utf-8")
