"""Job Profiler Agent (Phase 2).

Extracts required/preferred qualifications, tech stack, and seniority from a
raw job posting into a structured JobProfile.
"""

from __future__ import annotations

from typing import Any

from resume_tailor.agents.llm import DEFAULT_MODEL, get_client, parse_structured
from resume_tailor.schemas.job import RawJobPosting
from resume_tailor.schemas.job_profile import JobProfile

SYSTEM_PROMPT = (
    "You are a job posting analyst. Read the job posting text and extract its "
    "requirements into the given schema. List required qualifications and "
    "preferred/bonus qualifications as separate, distinct items — do not merge "
    "them. Capture every named technology, tool, or platform in tech_stack. "
    "keyword_index should be a flat list of every skill, technology, and "
    "qualification keyword useful for matching against a resume."
)


def profile_job(
    posting: RawJobPosting,
    *,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
) -> JobProfile:
    client = client or get_client()
    return parse_structured(
        client,
        model=model,
        system=SYSTEM_PROMPT,
        user_content=posting.raw_text,
        schema=JobProfile,
    )
