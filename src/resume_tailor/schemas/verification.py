"""Schema for the Verification/Anti-Hallucination Agent's output (Phase 3)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BulletVerification(BaseModel):
    tailored_text: str = Field(description="The tailored bullet text this verification applies to")
    entailment_score: float = Field(
        ge=0.0, le=1.0, description="1.0 = fully supported by the source bullet, 0.0 = unsupported"
    )
    passed: bool
    issues: list[str] = Field(
        default_factory=list,
        description="Specific fabricated/unsupported claims found (tools, metrics, titles, etc.), if any",
    )


class VerificationReport(BaseModel):
    bullet_verifications: list[BulletVerification] = Field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """Derived, not model-reported — an aggregate the LLM might get wrong on its own."""
        return all(v.passed for v in self.bullet_verifications)
