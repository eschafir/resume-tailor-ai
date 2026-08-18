from __future__ import annotations

import pymupdf
import pytest

from resume_tailor.errors import CorruptPDFError, MissingResumeSectionError
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


def test_parse_resume_pdf_recognizes_alternate_headings(tmp_path):
    """Real-world resumes use many phrasings for the same section — this
    guards against regressions in that heading-matching flexibility."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 60), "Jane Doe", fontsize=16)
    page.insert_text((50, 90), "jane@example.com", fontsize=10)
    page.insert_text((50, 140), "Career History", fontsize=13)
    page.insert_text((50, 160), "Acme Corp - Did things.", fontsize=10)
    page.insert_text((50, 210), "Academic Background", fontsize=13)
    page.insert_text((50, 230), "State University, 2016", fontsize=10)
    page.insert_text((50, 280), "Key Skills", fontsize=13)
    page.insert_text((50, 300), "Python, Go", fontsize=10)
    path = tmp_path / "alt_headings.pdf"
    doc.save(str(path))
    doc.close()

    parsed = parse_resume_pdf(str(path))

    present_types = {s.section_type for s in parsed.sections}
    assert SectionType.EXPERIENCE in present_types
    assert SectionType.EDUCATION in present_types
    assert SectionType.SKILLS in present_types


def test_parse_resume_pdf_letter_spaced_heading(tmp_path):
    """Some templates render headings as letter-spaced caps (E X P E R I E N C E)."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 60), "Jane Doe", fontsize=16)
    page.insert_text((50, 140), "E X P E R I E N C E", fontsize=13)
    page.insert_text((50, 160), "Acme Corp - Did things.", fontsize=10)
    page.insert_text((50, 210), "E D U C A T I O N", fontsize=13)
    page.insert_text((50, 230), "State University, 2016", fontsize=10)
    page.insert_text((50, 280), "S K I L L S", fontsize=13)
    page.insert_text((50, 300), "Python, Go", fontsize=10)
    path = tmp_path / "letter_spaced.pdf"
    doc.save(str(path))
    doc.close()

    parsed = parse_resume_pdf(str(path))

    present_types = {s.section_type for s in parsed.sections}
    assert SectionType.EXPERIENCE in present_types
    assert SectionType.EDUCATION in present_types
    assert SectionType.SKILLS in present_types


def test_parse_resume_pdf_missing_section_raises_typed_error(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 60), "Jane Doe", fontsize=16)
    page.insert_text(
        (50, 90), "A short bio paragraph with no recognizable section headings at all.", fontsize=10
    )
    path = tmp_path / "no_sections.pdf"
    doc.save(str(path))
    doc.close()

    with pytest.raises(MissingResumeSectionError) as exc_info:
        parse_resume_pdf(str(path))
    assert "experience" in exc_info.value.missing
