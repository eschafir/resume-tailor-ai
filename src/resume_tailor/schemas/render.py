"""The flattened, typesetting-ready resume structure (Phase 4).

Consumed directly by the Typst template as JSON — every field maps 1:1 onto
a rendered section so the template stays a pure presentation layer.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RenderableExperience(BaseModel):
    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[str] = Field(default_factory=list)


class RenderableEducation(BaseModel):
    institution: str
    degree: str
    field_of_study: str | None = None
    graduation_date: str | None = None


class RenderableProject(BaseModel):
    name: str
    bullets: list[str] = Field(default_factory=list)


class RenderableResume(BaseModel):
    full_name: str
    contact_summary: str | None = None
    summary: str | None = None
    experience: list[RenderableExperience] = Field(default_factory=list)
    education: list[RenderableEducation] = Field(default_factory=list)
    hard_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    projects: list[RenderableProject] = Field(default_factory=list)
