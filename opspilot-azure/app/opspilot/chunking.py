"""Split markdown documents into overlapping chunks for embedding."""

from __future__ import annotations

import re
from dataclasses import dataclass

HEADING = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    source: str
    index: int
    heading: str
    text: str


def _sections(markdown: str) -> list[tuple[str, str]]:
    """Return (heading, body) pairs. Text before the first heading gets an empty heading."""
    matches = list(HEADING.finditer(markdown))
    if not matches:
        return [("", markdown.strip())] if markdown.strip() else []
    sections: list[tuple[str, str]] = []
    preamble = markdown[: matches[0].start()].strip()
    if preamble:
        sections.append(("", preamble))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[m.end():end].strip()
        if body:
            sections.append((m.group(1).strip(), body))
    return sections


def chunk_markdown(source: str, markdown: str, max_words: int = 220, overlap: int = 40) -> list[Chunk]:
    """Chunk by heading first, then split long sections into word windows with overlap."""
    if overlap >= max_words:
        raise ValueError("overlap must be smaller than max_words")
    chunks: list[Chunk] = []
    for heading, body in _sections(markdown):
        words = body.split()
        start = 0
        while start < len(words):
            window = words[start:start + max_words]
            text = (f"{heading}\n" if heading else "") + " ".join(window)
            chunks.append(Chunk(source=source, index=len(chunks), heading=heading, text=text))
            if start + max_words >= len(words):
                break
            start += max_words - overlap
    return chunks
