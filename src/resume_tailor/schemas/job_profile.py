"""Schema for the structured job profile (Phase 2 — Job Profiler Agent)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SeniorityTier(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    STAFF_PLUS = "staff_plus"
    UNSPECIFIED = "unspecified"


class JobProfile(BaseModel):
    title: str
    company: str | None = None
    role_summary: str
    required_qualifications: list[str] = Field(default_factory=list)
    preferred_qualifications: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    seniority: SeniorityTier = SeniorityTier.UNSPECIFIED
    keyword_index: list[str] = Field(
        default_factory=list, description="Flat list of notable keywords/skills for matching"
    )
