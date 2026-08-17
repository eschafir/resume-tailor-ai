"""Schema for raw ingested job postings (Phase 1).

Structured requirement extraction (skills, seniority, qualifications) is the
Job Profiler Agent's responsibility in Phase 2. Phase 1 only guarantees the
full posting body was captured, free of site navigation boilerplate.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

MIN_POSTING_LENGTH = 200


class JobSourceType(str, Enum):
    PDF = "pdf"
    URL = "url"


class ExtractionMethod(str, Enum):
    PDF_TEXT = "pdf_text"
    STATIC_HTML = "static_html"
    RENDERED_SPA = "rendered_spa"


class RawJobPosting(BaseModel):
    """The complete extracted body of a target job posting."""

    source_type: JobSourceType
    source: str = Field(min_length=1, description="Filename or URL the posting came from")
    raw_text: str = Field(min_length=MIN_POSTING_LENGTH)
    title: str | None = None
    extraction_method: ExtractionMethod
    fetched_at: datetime

    @field_validator("raw_text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("raw_text must not be blank/whitespace-only")
        return v
