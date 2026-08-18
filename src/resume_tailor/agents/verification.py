"""Verification / Anti-Hallucination Agent (Phase 3).

Performs strict bidirectional entailment checks between each tailored bullet
and its own source bullet, to guarantee no metrics, skills, tools, or roles
are fabricated during tailoring.
"""

from __future__ import annotations

from typing import Any

from resume_tailor.agents.llm import DEFAULT_MODEL, get_client, parse_structured
from resume_tailor.schemas.tailoring import TailoredResume
from resume_tailor.schemas.verification import VerificationReport

SYSTEM_PROMPT = (
    "You are a strict fact-checking critic for resume rewrites. For each "
    "tailored bullet, compare its tailored_text against its own "
    "original_text and determine whether every claim in tailored_text is "
    "entailed by (supported by) original_text. "
    "Flag as an issue any tool, technology, employer, job title, "
    "certification, or numeric metric (percentage, dollar amount, count, "
    "duration) that appears in tailored_text but does NOT appear in, and is "
    "not a reasonable paraphrase of, original_text. Rephrasing for clarity "
    "or reframing existing facts is fine and must NOT be flagged. "
    "Score entailment_score from 0.0 (completely unsupported) to 1.0 (fully "
    "supported); set passed to true only if entailment_score is at least "
    "0.8 AND issues is empty. Include one BulletVerification entry per "
    "tailored bullet given, in the same order."
)


def verify_tailored_resume(
    tailored_resume: TailoredResume,
    *,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
) -> VerificationReport:
    client = client or get_client()
    return parse_structured(
        client,
        model=model,
        system=SYSTEM_PROMPT,
        user_content=tailored_resume.model_dump_json(indent=2),
        schema=VerificationReport,
    )
