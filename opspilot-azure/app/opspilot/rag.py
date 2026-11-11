"""The question-answering pipeline: guardrails -> retrieve -> generate -> redact."""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Settings
from .guardrails import check_question, redact
from .llm import LLMClient
from .metrics import GUARDRAIL_BLOCKS, NO_CONTEXT, REDACTIONS, RETRIEVAL_DISTANCE
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .store import VectorStore

NO_ANSWER = "I don't have a runbook for that yet."


@dataclass
class Answer:
    answer: str
    sources: list[str] = field(default_factory=list)
    blocked: bool = False
    reason: str = ""
    tokens: int = 0


class RagPipeline:
    def __init__(self, settings: Settings, llm: LLMClient, store: VectorStore):
        self.s, self.llm, self.store = settings, llm, store

    def ask(self, question: str) -> Answer:
        check = check_question(question, self.s.max_question_chars)
        if not check.allowed:
            GUARDRAIL_BLOCKS.labels(check.reason).inc()
            return Answer(answer="Request blocked by guardrails.", blocked=True, reason=check.reason)

        [q_emb] = self.llm.embed([question])
        hits = self.store.search(q_emb, self.s.top_k)
        if hits:
            RETRIEVAL_DISTANCE.observe(hits[0]["distance"])
        relevant = [h for h in hits if h["distance"] <= self.s.max_distance]
        if not relevant:
            NO_CONTEXT.inc()
            return Answer(answer=NO_ANSWER)

        result = self.llm.chat(SYSTEM_PROMPT, build_user_prompt(question, relevant))
        clean, kinds = redact(result.text)
        for kind in kinds:
            REDACTIONS.labels(kind).inc()
        sources = sorted({h["source"] for h in relevant})
        return Answer(answer=clean, sources=sources, tokens=result.prompt_tokens + result.completion_tokens)
