from __future__ import annotations

import pytest

from resume_tailor.errors import CorruptPDFError
from resume_tailor.ingestion.pdf_parser import parse_job_pdf, parse_resume_pdf
from resume_tailor.schemas.document import SectionType
from tests.fixtures import generate_pdfs


def test_pdf_resume_extraction_completeness(resume_pdf_path):
    parsed = parse_resume_pdf(resume_pdf_path)

    present_types = {s.section_type for s in parsed.sections}
    assert present_types >= {
        SectionType.CONTACT,
        SectionType.SUMMARY,
        SectionType.EXPERIENCE,
        SectionType.EDUCATION,
        SectionType.SKILLS,
        SectionType.PROJECTS,
    }

    full_text = parsed.full_text
    assert generate_pdfs.CONTACT_NAME in full_text
    assert generate_pdfs.CONTACT_LINE in full_text
    assert generate_pdfs.SUMMARY_TEXT in full_text
    assert generate_pdfs.EDUCATION_TEXT in full_text
    assert generate_pdfs.SKILLS_TEXT in full_text
    for title, bullets in generate_pdfs.EXPERIENCE_ENTRIES:
        assert title in full_text
        for bullet in bullets:
            assert bullet in full_text
    for title, bullets in generate_pdfs.PROJECTS_ENTRIES:
        assert title in full_text
        for bullet in bullets:
            assert bullet in full_text


def test_pdf_resume_extraction_reports_correct_page_count(resume_pdf_path):
    parsed = parse_resume_pdf(resume_pdf_path)
    assert parsed.page_count >= 1


def test_corrupt_resume_pdf_raises_typed_error(corrupt_pdf_path):
    with pytest.raises(CorruptPDFError):
        parse_resume_pdf(corrupt_pdf_path)


def test_missing_resume_pdf_raises_typed_error():
    with pytest.raises(CorruptPDFError):
        parse_resume_pdf("/nonexistent/path/does-not-exist.pdf")


def test_job_pdf_extracts_complete_posting_body(job_pdf_path):
    posting = parse_job_pdf(job_pdf_path)
    assert generate_pdfs.JOB_TITLE in posting.raw_text
    assert generate_pdfs.JOB_COMPANY in posting.raw_text
    for paragraph in generate_pdfs.JOB_BODY_PARAGRAPHS:
        assert paragraph in posting.raw_text


def test_corrupt_job_pdf_raises_typed_error(corrupt_pdf_path):
    with pytest.raises(CorruptPDFError):
        parse_job_pdf(corrupt_pdf_path)
