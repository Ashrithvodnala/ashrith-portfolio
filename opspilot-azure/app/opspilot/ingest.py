"""Load markdown runbooks into pgvector.  Usage:  python -m opspilot.ingest ./docs/runbooks"""

from __future__ import annotations

import sys
from pathlib import Path

from .chunking import chunk_markdown
from .config import Settings, load_settings
from .guardrails import redact
from .llm import LLMClient
from .metrics import REDACTIONS
from .store import VectorStore

BATCH = 16


def ingest_directory(path: Path, settings: Settings, llm: LLMClient, store: VectorStore) -> dict:
    store.init_schema()
    files = sorted(path.rglob("*.md"))
    total = 0
    for f in files:
        text, kinds = redact(f.read_text(encoding="utf-8"))  # never store secrets in the vector DB
        for kind in kinds:
            REDACTIONS.labels(kind).inc()
        chunks = chunk_markdown(f.name, text)
        contents = [c.text for c in chunks]
        embeddings: list[list[float]] = []
        for i in range(0, len(contents), BATCH):
            embeddings.extend(llm.embed(contents[i:i + BATCH]))
        store.replace_source(f.name, contents, embeddings)
        total += len(chunks)
        print(f"ingested {f.name}: {len(chunks)} chunks")
    return {"files": len(files), "chunks": total}


def main() -> None:
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/runbooks")
    s = load_settings()
    print(ingest_directory(folder, s, LLMClient(s), VectorStore(s.database_url, s.embedding_dim)))


if __name__ == "__main__":
    main()
