"""Resume Profiler Agent (Phase 2).

Deconstructs the parsed resume into structured work history, education,
skills, and projects — decomposing each bullet into its action verb, tools,
and metrics.
"""

from __future__ import annotations

from typing import Any

from resume_tailor.agents.llm import DEFAULT_MODEL, get_client, parse_structured
from resume_tailor.schemas.candidate import CandidateProfile
from resume_tailor.schemas.document import ParsedResume

SYSTEM_PROMPT = (
    "You are a resume analyst. Read the sectioned resume text and extract it "
    "into the given schema. For every bullet point under Experience and "
    "Projects, decompose it into its leading action verb, any tools/"
    "technologies it names, and any quantified metrics it names (percentages, "
    "dollar amounts, counts, durations). Preserve the bullet's original text "
    "verbatim in the 'text' field. Only extract facts present in the resume — "
    "never invent employers, titles, dates, tools, or metrics."
)


def _render_sections(parsed: ParsedResume) -> str:
    return "\n\n".join(f"## {s.section_type.value}\n{s.text}" for s in parsed.sections)


def profile_resume(
    parsed_resume: ParsedResume,
    *,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
) -> CandidateProfile:
    client = client or get_client()
    return parse_structured(
        client,
        model=model,
        system=SYSTEM_PROMPT,
        user_content=_render_sections(parsed_resume),
        schema=CandidateProfile,
    )
