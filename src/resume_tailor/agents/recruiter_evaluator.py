"""Recruiter / Evaluator Agent (Phase 2).

Performs gap analysis between the candidate profile and job profile,
producing a fit score and a strategic delta roadmap.
"""

from __future__ import annotations

from typing import Any

from resume_tailor.agents.llm import DEFAULT_MODEL, get_client, parse_structured
from resume_tailor.schemas.candidate import CandidateProfile
from resume_tailor.schemas.evaluation import DeltaReport
from resume_tailor.schemas.job_profile import JobProfile

SYSTEM_PROMPT = (
    "You are a technical recruiter performing a gap analysis between a "
    "candidate's resume and a target job. Compare the candidate profile "
    "against the job profile. Identify which required/preferred "
    "qualifications the candidate already matches, which keywords from the "
    "job are missing from the resume, and produce a fit_score from 0-100. "
    "For each notable gap or alignment opportunity, add a recommendation "
    "naming the specific resume bullet or section to rephrase, highlight, or "
    "de-emphasize, and why. Keep each recommendation's instruction to one or "
    "two sentences. Base every judgment strictly on the two profiles given — "
    "never invent candidate experience that isn't there."
)


def evaluate_gap(
    job_profile: JobProfile,
    candidate_profile: CandidateProfile,
    *,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
) -> DeltaReport:
    client = client or get_client()
    user_content = (
        f"## Job Profile\n{job_profile.model_dump_json(indent=2)}\n\n"
        f"## Candidate Profile\n{candidate_profile.model_dump_json(indent=2)}"
    )
    return parse_structured(
        client,
        model=model,
        system=SYSTEM_PROMPT,
        user_content=user_content,
        schema=DeltaReport,
    )
