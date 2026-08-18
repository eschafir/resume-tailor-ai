"""Schema for the structured candidate profile (Phase 2 — Resume Profiler Agent).

Decomposes each resume bullet into its action verb, tools, and metrics so the
Recruiter/Evaluator and Tailoring agents can reason over structured claims
instead of raw text.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BulletPoint(BaseModel):
    text: str = Field(description="The original bullet point text, verbatim from the resume")
    action_verb: str = Field(description="The leading action verb, e.g. 'Led', 'Built', 'Reduced'")
    tools: list[str] = Field(default_factory=list, description="Technical tools/technologies mentioned")
    metrics: list[str] = Field(
        default_factory=list, description="Quantified metrics mentioned, e.g. '30%', '$2M', '12 teams'"
    )


class ExperienceEntry(BaseModel):
    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[BulletPoint] = Field(default_factory=list)


class EducationEntry(BaseModel):
    institution: str
    degree: str
    field_of_study: str | None = None
    graduation_date: str | None = None


class ProjectEntry(BaseModel):
    name: str
    bullets: list[BulletPoint] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    full_name: str | None = None
    contact_summary: str | None = Field(
        default=None, description="Email/phone/location as found on the resume"
    )
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    hard_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
