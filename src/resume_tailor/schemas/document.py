"""Schemas for layout-aware resume extraction (Phase 1).

These models capture *structural* completeness — every text block from the
source PDF is accounted for and assigned to a section. Deeper semantic
decomposition (action verbs, tools, metrics per bullet) is the Resume
Profiler Agent's job in Phase 2.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class SectionType(str, Enum):
    CONTACT = "contact"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    PROJECTS = "projects"
    OTHER = "other"


REQUIRED_SECTION_TYPES = (
    SectionType.CONTACT,
    SectionType.EXPERIENCE,
    SectionType.EDUCATION,
    SectionType.SKILLS,
)


class TextBlock(BaseModel):
    """A single layout-positioned block of text as emitted by the PDF parser."""

    text: str = Field(min_length=1)
    page: int = Field(ge=0)
    bbox: tuple[float, float, float, float]
    block_index: int = Field(ge=0)

    @field_validator("text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text block must not be blank/whitespace-only")
        return v


class ResumeSection(BaseModel):
    """A resume section (e.g. Experience) and the text blocks assigned to it."""

    section_type: SectionType
    heading: str | None = None
    blocks: list[TextBlock] = Field(min_length=1)

    @property
    def text(self) -> str:
        return "\n".join(b.text for b in self.blocks)


class ParsedResume(BaseModel):
    """Structured, layout-aware output of the resume ingestion pipeline."""

    source_filename: str
    page_count: int = Field(ge=1)
    sections: list[ResumeSection] = Field(min_length=1)

    @property
    def full_text(self) -> str:
        return "\n\n".join(s.text for s in self.sections)

    @model_validator(mode="after")
    def _required_sections_present(self) -> "ParsedResume":
        present = {s.section_type for s in self.sections}
        missing = [s.value for s in REQUIRED_SECTION_TYPES if s not in present]
        if missing:
            raise ValueError(
                f"ParsedResume is missing required section(s): {', '.join(missing)}"
            )
        return self
