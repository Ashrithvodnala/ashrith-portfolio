"""FastAPI service: chat UI, /ask, /ingest, health probes and /metrics."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from prometheus_client import make_asgi_app
from pydantic import BaseModel

from .config import load_settings
from .ingest import ingest_directory
from .llm import LLMClient
from .metrics import REQUESTS
from .rag import RagPipeline
from .store import VectorStore

settings = load_settings()
state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = VectorStore(settings.database_url, settings.embedding_dim)
    llm = LLMClient(settings)
    try:
        store.init_schema()
    except Exception as exc:  # DB may not be ready yet; /readyz reports it
        print(f"schema init deferred: {exc}")
    state.update(store=store, llm=llm, rag=RagPipeline(settings, llm, store))
    yield


app = FastAPI(title="OpsPilot", version="0.1.0", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())


class Question(BaseModel):
    question: str


@app.post("/ask")
def ask(q: Question):
    try:
        ans = state["rag"].ask(q.question)
    except Exception as exc:
        REQUESTS.labels("ask", "error").inc()
        raise HTTPException(status_code=502, detail="LLM or database unavailable") from exc
    REQUESTS.labels("ask", "blocked" if ans.blocked else "ok").inc()
    return ans.__dict__


@app.post("/ingest")
def ingest(x_admin_token: str = Header(default="")):
    if not settings.admin_token or x_admin_token != settings.admin_token:
        REQUESTS.labels("ingest", "forbidden").inc()
        raise HTTPException(status_code=403, detail="forbidden")
    docs = Path(os.getenv("DOCS_DIR", "/app/docs/runbooks"))
    result = ingest_directory(docs, settings, state["llm"], state["store"])
    REQUESTS.labels("ingest", "ok").inc()
    return result


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    try:
        state["store"].ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database not ready") from exc
    return {"status": "ready", "provider": settings.llm_provider, "chunks": state["store"].count()}


@app.get("/", response_class=HTMLResponse)
def ui():
    return (Path(__file__).parent / "ui.html").read_text(encoding="utf-8")
