from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from resume_tailor.schemas.document import ParsedResume, ResumeSection, SectionType, TextBlock
from resume_tailor.schemas.job import ExtractionMethod, JobSourceType, RawJobPosting


def _block(text: str, index: int = 0) -> TextBlock:
    return TextBlock(text=text, page=0, bbox=(0, 0, 100, 10), block_index=index)


def _valid_sections() -> list[ResumeSection]:
    return [
        ResumeSection(section_type=SectionType.CONTACT, blocks=[_block("Jane Doe")]),
        ResumeSection(section_type=SectionType.EXPERIENCE, heading="Experience", blocks=[_block("Did things")]),
        ResumeSection(section_type=SectionType.EDUCATION, heading="Education", blocks=[_block("B.S. CS")]),
        ResumeSection(section_type=SectionType.SKILLS, heading="Skills", blocks=[_block("Python")]),
    ]


def test_schema_validation_success_and_failure():
    # Success: a payload with all required sections present validates cleanly.
    parsed = ParsedResume(
        source_filename="resume.pdf",
        page_count=1,
        sections=_valid_sections(),
    )
    assert parsed.full_text  # non-empty, all sections concatenated

    # Failure: dropping a required section (Education) must raise ValidationError.
    incomplete_sections = [s for s in _valid_sections() if s.section_type != SectionType.EDUCATION]
    with pytest.raises(ValidationError):
        ParsedResume(
            source_filename="resume.pdf",
            page_count=1,
            sections=incomplete_sections,
        )


def test_text_block_rejects_blank_text():
    with pytest.raises(ValidationError):
        TextBlock(text="   ", page=0, bbox=(0, 0, 1, 1), block_index=0)


def test_resume_section_rejects_empty_blocks():
    with pytest.raises(ValidationError):
        ResumeSection(section_type=SectionType.SKILLS, blocks=[])


def test_raw_job_posting_success_and_failure():
    valid = RawJobPosting(
        source_type=JobSourceType.URL,
        source="https://example.com/jobs/123",
        raw_text="x" * 250,
        extraction_method=ExtractionMethod.STATIC_HTML,
        fetched_at=datetime.now(timezone.utc),
    )
    assert len(valid.raw_text) >= 200

    with pytest.raises(ValidationError):
        RawJobPosting(
            source_type=JobSourceType.URL,
            source="https://example.com/jobs/123",
            raw_text="too short",
            extraction_method=ExtractionMethod.STATIC_HTML,
            fetched_at=datetime.now(timezone.utc),
        )
