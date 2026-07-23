"""AI provider abstraction — no vendor hardcoding.

Current phase uses a deterministic rule engine.
Future providers (OpenAI, Azure OpenAI, etc.) plug in via this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CONFLICT = "conflict"
    NO_MATCH = "no_match"


class AssociationEvidence(BaseModel):
    signal: str
    value: str
    weight: float = 0.0
    notes: Optional[str] = None


class AssociationResult(BaseModel):
    suggested_primary_matter_id: Optional[str] = None
    suggested_secondary_matter_ids: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.NO_MATCH
    evidence: list[AssociationEvidence] = Field(default_factory=list)
    conflicting_matter_ids: list[str] = Field(default_factory=list)
    processing_status: str = "completed"
    raw: dict[str, Any] = Field(default_factory=dict)


class SummarizationRequest(BaseModel):
    text: str
    context: Optional[dict[str, Any]] = None


class SummarizationResult(BaseModel):
    summary: str
    provider: str
    model: Optional[str] = None


class EmbeddingRequest(BaseModel):
    texts: list[str]


class EmbeddingResult(BaseModel):
    vectors: list[list[float]]
    provider: str
    model: Optional[str] = None
    dimensions: int = 0


class AIProvider(ABC):
    """Pluggable AI capability interface."""

    name: str

    @abstractmethod
    def associate_matter(
        self, signals: dict[str, Any], candidates: list[dict[str, Any]]
    ) -> AssociationResult:
        raise NotImplementedError

    @abstractmethod
    def summarize(self, request: SummarizationRequest) -> SummarizationResult:
        raise NotImplementedError

    @abstractmethod
    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        raise NotImplementedError


class RuleEngineAIProvider(AIProvider):
    """Deterministic rule-based provider used for MVP. No external API calls."""

    name = "rule_engine"

    def associate_matter(
        self, signals: dict[str, Any], candidates: list[dict[str, Any]]
    ) -> AssociationResult:
        evidence: list[AssociationEvidence] = []
        matches: dict[str, float] = {}

        exact_keys = (
            "claim_number",
            "policy_number",
            "case_number",
            "appraisal_number",
        )
        for key in exact_keys:
            signal_val = (signals.get(key) or "").strip().lower()
            if not signal_val:
                continue
            for candidate in candidates:
                cand_val = str(candidate.get(key) or "").strip().lower()
                if cand_val and cand_val == signal_val:
                    mid = str(candidate["id"])
                    matches[mid] = matches.get(mid, 0.0) + 0.35
                    evidence.append(
                        AssociationEvidence(
                            signal=key,
                            value=signal_val,
                            weight=0.35,
                            notes=f"Exact match on {key}",
                        )
                    )

        if not matches:
            return AssociationResult(confidence_level=ConfidenceLevel.NO_MATCH)

        ranked = sorted(matches.items(), key=lambda x: x[1], reverse=True)
        top_id, top_score = ranked[0]
        conflicts = [mid for mid, score in ranked[1:] if abs(score - top_score) < 0.05]

        if conflicts:
            level = ConfidenceLevel.CONFLICT
        elif top_score >= 0.7:
            level = ConfidenceLevel.HIGH
        elif top_score >= 0.4:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW

        return AssociationResult(
            suggested_primary_matter_id=None if conflicts else top_id,
            suggested_secondary_matter_ids=[m for m, _ in ranked[1:3]],
            confidence_score=min(top_score, 1.0),
            confidence_level=level,
            evidence=evidence,
            conflicting_matter_ids=conflicts,
        )

    def summarize(self, request: SummarizationRequest) -> SummarizationResult:
        """Extractive summary: first line + key bullets from dense text."""
        text = (request.text or "").strip()
        if not text:
            return SummarizationResult(
                summary="No content to summarize.",
                provider=self.name,
                model="extractive-v1",
            )
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        head = lines[0] if lines else ""
        # Prefer lines with claim/policy/email/document keywords
        keywords = ("claim", "policy", "email", "document", "expense", "mileage", "billing", "status")
        bullets: list[str] = []
        for ln in lines[1:]:
            low = ln.lower()
            if any(k in low for k in keywords) or len(bullets) < 3:
                short = ln if len(ln) <= 160 else ln[:157] + "…"
                if short not in bullets:
                    bullets.append(short)
            if len(bullets) >= 6:
                break
        if not bullets:
            snippet = text[:400] + ("…" if len(text) > 400 else "")
            summary = snippet
        else:
            summary = head + "\n• " + "\n• ".join(bullets[:6])
        return SummarizationResult(
            summary=summary[:2500],
            provider=self.name,
            model="extractive-v1",
        )

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        # Placeholder zero vectors — real embeddings arrive with an AI vendor provider.
        dims = 8
        return EmbeddingResult(
            vectors=[[0.0] * dims for _ in request.texts],
            provider=self.name,
            model="noop",
            dimensions=dims,
        )


def get_ai_provider() -> AIProvider:
    """Factory — swap providers via config in later phases without refactoring callers."""
    return RuleEngineAIProvider()
