"""Layout-aware PDF parsing for resumes and job postings, via PyMuPDF."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

import pymupdf as fitz

from resume_tailor.errors import CorruptPDFError, InsufficientContentError
from resume_tailor.schemas.document import ParsedResume, ResumeSection, SectionType, TextBlock
from resume_tailor.schemas.job import ExtractionMethod, JobSourceType, RawJobPosting, MIN_POSTING_LENGTH

# Section headings are short standalone lines. Longer matches (e.g. a bullet
# point that happens to mention "skills") must not be misclassified.
_MAX_HEADING_LENGTH = 40

_HEADING_KEYWORDS: dict[SectionType, tuple[str, ...]] = {
    SectionType.SUMMARY: ("summary", "objective", "profile", "professional summary"),
    SectionType.EXPERIENCE: (
        "experience",
        "work experience",
        "professional experience",
        "employment history",
    ),
    SectionType.EDUCATION: ("education", "academic background"),
    SectionType.SKILLS: ("skills", "technical skills", "core competencies"),
    SectionType.PROJECTS: ("projects", "personal projects", "selected projects"),
}


def _open_pdf(path: str) -> fitz.Document:
    if not os.path.exists(path):
        raise CorruptPDFError(path, "file does not exist")
    try:
        doc = fitz.open(path)
    except Exception as exc:  # PyMuPDF raises various fitz/mupdf errors
        raise CorruptPDFError(path, str(exc)) from exc
    if doc.is_encrypted:
        raise CorruptPDFError(path, "PDF is encrypted/password-protected")
    return doc


def _extract_text_blocks(doc: fitz.Document) -> list[TextBlock]:
    blocks: list[TextBlock] = []
    index = 0
    for page_num, page in enumerate(doc):
        raw_blocks = page.get_text("blocks")
        # Reading order: top-to-bottom, then left-to-right.
        raw_blocks.sort(key=lambda b: (round(b[1], 1), round(b[0], 1)))
        for x0, y0, x1, y1, text, *_rest in raw_blocks:
            cleaned = text.strip()
            if not cleaned:
                continue
            blocks.append(
                TextBlock(
                    text=cleaned,
                    page=page_num,
                    bbox=(x0, y0, x1, y1),
                    block_index=index,
                )
            )
            index += 1
    return blocks


def _classify_heading(text: str) -> tuple[SectionType, str] | None:
    """Detect a section heading from a block's first line.

    PyMuPDF frequently clusters a heading together with the paragraph that
    immediately follows it into a single block, so headings can't be
    identified by requiring the *entire* block to be a short line — only
    the first line is checked.
    """
    first_line = text.split("\n", 1)[0].strip()
    if not first_line or len(first_line) > _MAX_HEADING_LENGTH:
        return None
    normalized = re.sub(r"[:\-–—]+$", "", first_line.lower()).strip()
    for section_type, keywords in _HEADING_KEYWORDS.items():
        if normalized in keywords:
            return section_type, first_line
    return None


def _group_into_sections(blocks: list[TextBlock]) -> list[ResumeSection]:
    if not blocks:
        return []

    sections: list[ResumeSection] = []
    current_type = SectionType.CONTACT
    current_heading: str | None = None
    current_blocks: list[TextBlock] = []

    for block in blocks:
        detected = _classify_heading(block.text)
        if detected is not None and detected[0] != current_type:
            if current_blocks:
                sections.append(
                    ResumeSection(
                        section_type=current_type,
                        heading=current_heading,
                        blocks=current_blocks,
                    )
                )
            current_type, current_heading = detected
            current_blocks = [block]
        else:
            current_blocks.append(block)

    if current_blocks:
        sections.append(
            ResumeSection(
                section_type=current_type,
                heading=current_heading,
                blocks=current_blocks,
            )
        )

    return sections


def parse_resume_pdf(path: str) -> ParsedResume:
    """Parse a resume PDF into layout-aware, section-classified text blocks."""
    doc = _open_pdf(path)
    try:
        blocks = _extract_text_blocks(doc)
        if not blocks:
            raise CorruptPDFError(path, "no extractable text found (possibly a scanned image PDF)")
        sections = _group_into_sections(blocks)
        return ParsedResume(
            source_filename=os.path.basename(path),
            page_count=doc.page_count,
            sections=sections,
        )
    finally:
        doc.close()


def parse_job_pdf(path: str) -> RawJobPosting:
    """Parse a target job posting PDF into its complete raw text body."""
    doc = _open_pdf(path)
    try:
        pages_text = [page.get_text("text").strip() for page in doc]
        raw_text = "\n\n".join(t for t in pages_text if t)
        if len(raw_text) < MIN_POSTING_LENGTH:
            raise InsufficientContentError(path, len(raw_text))
        return RawJobPosting(
            source_type=JobSourceType.PDF,
            source=os.path.basename(path),
            raw_text=raw_text,
            extraction_method=ExtractionMethod.PDF_TEXT,
            fetched_at=datetime.now(timezone.utc),
        )
    finally:
        doc.close()
