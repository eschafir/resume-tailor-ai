"""Schema for the Recruiter/Evaluator Agent's gap analysis (Phase 2)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OptimizationDirective(BaseModel):
    target: str = Field(description="Which resume bullet/section this directive applies to")
    instruction: str = Field(description="What to rephrase, highlight, or de-emphasize, and why")


class DeltaReport(BaseModel):
    fit_score: int = Field(ge=0, le=100)
    matched_qualifications: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    keyword_alignment_map: dict[str, str] = Field(
        default_factory=dict, description="Resume term -> matching job requirement term"
    )
    recommendations: list[OptimizationDirective] = Field(default_factory=list)
