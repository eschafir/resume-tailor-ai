"""Tailoring / Copywriting Agent (Phase 3).

Rewrites resume bullets to map onto job requirements using XYZ/STAR impact
formatting, guided by the Recruiter/Evaluator's gap analysis. Never invents
new tools, employers, titles, or metrics — the Verification Agent enforces
that boundary downstream, and any bullet it rejects is fed back here for
regeneration.
"""

from __future__ import annotations

from typing import Any

from resume_tailor.agents.llm import DEFAULT_MODEL, get_client, parse_structured
from resume_tailor.schemas.candidate import CandidateProfile
from resume_tailor.schemas.evaluation import DeltaReport
from resume_tailor.schemas.tailoring import TailoredResume
from resume_tailor.schemas.verification import VerificationReport

SYSTEM_PROMPT = (
    "You are a resume copywriter. Rewrite the candidate's experience and "
    "project bullet points to align with the target job's keywords and "
    "requirements, using an action-driven XYZ/STAR formula ('Accomplished "
    "[X] as measured by [Y], by doing [Z]'). Incorporate the job's missing "
    "keywords and tech stack naturally, but only where the candidate's "
    "original bullet already supports that claim. "
    "Preserve the candidate's original scope, seniority, and meaning — you "
    "may rephrase and re-emphasize, but you must NEVER invent a tool, "
    "employer, job title, or numeric metric that isn't already present in "
    "the original bullet. If a bullet has no relevant keyword to align to, "
    "still improve its clarity and impact framing without adding new claims. "
    "Include the exact original bullet text verbatim in original_text for "
    "every tailored bullet."
)


def tailor_bullets(
    candidate_profile: CandidateProfile,
    delta_report: DeltaReport,
    *,
    feedback: VerificationReport | None = None,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
) -> TailoredResume:
    client = client or get_client()
    user_content = (
        f"## Candidate Profile\n{candidate_profile.model_dump_json(indent=2)}\n\n"
        f"## Gap Analysis / Delta Report\n{delta_report.model_dump_json(indent=2)}"
    )
    failed = [v for v in feedback.bullet_verifications if not v.passed] if feedback else []
    if failed:
        issues_text = "\n".join(
            f'- "{v.tailored_text}" — {", ".join(v.issues) or "failed entailment check"}' for v in failed
        )
        user_content += (
            "\n\n## Regeneration required\n"
            "The previous attempt at the bullets below failed anti-hallucination "
            "verification. Rewrite ONLY these bullets again, fixing the issue named "
            "for each one — remove or replace any claim not present in the original "
            "bullet:\n"
            f"{issues_text}"
        )
    return parse_structured(
        client,
        model=model,
        system=SYSTEM_PROMPT,
        user_content=user_content,
        schema=TailoredResume,
    )
