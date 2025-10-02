from __future__ import annotations

import json
import logging
import os
import re
from typing import List, Sequence, Set

try:  # pragma: no cover - runtime import fallback
    from .models import PageContent, Span
except ImportError:  # pragma: no cover
    from models import PageContent, Span

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

logger = logging.getLogger(__name__)


VARIABLE_PATTERNS: List[re.Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"policy\s*(?:number|no\.?|#)\s*[:\-]?\s*\w+",
        r"claim\s*(?:number|no\.?|#)\s*[:\-]?\s*\w+",
        r"member\s*(?:id|number)\s*[:\-]?\s*\w+",
        r"(insured|customer|patient)\s*name\b",
        r"address[:\-]?\s*",
        r"effective\s*date\b",
        r"date\s*of\s*birth\b",
    ]
]

NUMERIC_HEURISTIC = re.compile(r"\b\d{4,}\b")
EMAIL_HEURISTIC = re.compile(r"[\w.]+@[\w.]+")
KEYWORD_TOKENS = (
    "policy",
    "claim",
    "member",
    "account",
    "invoice",
    "customer",
    "insured",
    "reference",
    "number",
    "id",
)


class VariableFieldFilter:
    def __init__(
        self,
        enable_llm: bool = False,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
    ) -> None:
        self.enable_llm = enable_llm and OpenAI is not None
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
        if self.enable_llm and self.api_key:
            try:
                self._client = OpenAI(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover
                logger.warning("Could not initialize OpenAI client: %s", exc)
                self.enable_llm = False

    def tag_variable_fields(self, pages: Sequence[PageContent]) -> None:
        for page in pages:
            heuristic_hits = self._apply_heuristics(page.spans)
            llm_hits: Set[int] = set()
            if self.enable_llm and page.spans:
                llm_hits = self._apply_llm_filter(page)
            for idx, span in enumerate(page.spans):
                if idx in heuristic_hits or idx in llm_hits:
                    span.is_variable = True

    def _apply_heuristics(self, spans: Sequence[Span]) -> Set[int]:
        hits: Set[int] = set()
        for idx, span in enumerate(spans):
            text = span.text.strip()
            if not text:
                continue
            normalized = text.lower()
            if any(pattern.search(text) for pattern in VARIABLE_PATTERNS):
                hits.add(idx)
                continue
            if NUMERIC_HEURISTIC.search(text) and any(token in normalized for token in KEYWORD_TOKENS):
                hits.add(idx)
                continue
            if EMAIL_HEURISTIC.search(text):
                hits.add(idx)
                continue
            if any(token in normalized for token in ("ssn", "tax id", "zip")):
                hits.add(idx)
        return hits

    def _apply_llm_filter(self, page: PageContent) -> Set[int]:
        if not self._client:
            return set()
        limited_spans = page.spans[:200]
        payload = [
            {"index": idx, "text": span.text}
            for idx, span in enumerate(limited_spans)
        ]
        prompt = (
            "You are assisting with PDF comparison. Given the list of text spans "
            "(with their indices) from an insurance document, identify which "
            "spans contain user-specific variable data such as names, addresses, "
            "IDs, or dates. Return a JSON array of indices only."
        )
        try:
            response = self._client.responses.create(  # type: ignore[call-arg]
                model=self.model,
                input=f"{prompt}\nSpans: {json.dumps(payload)}",
                max_output_tokens=200,
            )
            output = response.output[0].content[0].text  # type: ignore[attr-defined]
            indices = json.loads(output)
            if isinstance(indices, list):
                return {int(i) for i in indices if 0 <= int(i) < len(page.spans)}
        except Exception as exc:  # pragma: no cover
            logger.info("LLM variable filter skipped: %s", exc)
        return set()


__all__ = ["VariableFieldFilter"]
