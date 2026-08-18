"""Schema for the Tailoring/Copywriting Agent's output (Phase 3)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TailoredBullet(BaseModel):
    company: str = Field(
        description="Which experience entry (company) this bullet belongs to, or 'Projects'/'Summary'"
    )
    original_text: str = Field(description="The original bullet text, verbatim from the candidate profile")
    tailored_text: str = Field(
        description="The rewritten bullet, using XYZ/STAR impact formatting and job keywords"
    )
    keywords_incorporated: list[str] = Field(default_factory=list)


class TailoredResume(BaseModel):
    tailored_summary: str | None = None
    tailored_bullets: list[TailoredBullet] = Field(default_factory=list)
