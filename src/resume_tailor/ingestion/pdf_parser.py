"""Layout-aware PDF parsing for resumes and job postings, via PyMuPDF."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

import pydantic
import pymupdf as fitz

from resume_tailor.errors import CorruptPDFError, InsufficientContentError, MissingResumeSectionError
from resume_tailor.schemas.document import (
    REQUIRED_SECTION_TYPES,
    ParsedResume,
    ResumeSection,
    SectionType,
    TextBlock,
)
from resume_tailor.schemas.job import ExtractionMethod, JobSourceType, RawJobPosting, MIN_POSTING_LENGTH

# Section headings are short standalone lines. Longer matches (e.g. a bullet
# point that happens to mention "skills") must not be misclassified.
_MAX_HEADING_LENGTH = 40

# Real-world resumes use many different phrasings for the same section — this
# list is intentionally broad. Matching is by exact equality after
# normalization (see _normalize_heading_candidate), not substring, so a
# bullet point that happens to mention "skills" mid-sentence won't be
# misclassified as a new heading.
_HEADING_KEYWORDS: dict[SectionType, tuple[str, ...]] = {
    SectionType.SUMMARY: (
        "summary",
        "objective",
        "profile",
        "professional summary",
        "career summary",
        "career profile",
        "about me",
        "about",
        "highlights",
        "professional profile",
    ),
    SectionType.EXPERIENCE: (
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history",
        "career history",
        "relevant experience",
        "professional background",
        "employment",
        "career experience",
        "experience & education",
    ),
    SectionType.EDUCATION: (
        "education",
        "academic background",
        "academic history",
        "education & certifications",
        "academic qualifications",
        "educational background",
    ),
    SectionType.SKILLS: (
        "skills",
        "technical skills",
        "core competencies",
        "key skills",
        "areas of expertise",
        "competencies",
        "skills & tools",
        "skills and tools",
        "technologies",
        "technical proficiencies",
        "skills and expertise",
    ),
    SectionType.PROJECTS: (
        "projects",
        "personal projects",
        "selected projects",
        "notable projects",
        "key projects",
        "academic projects",
        "portfolio",
        "side projects",
    ),
}

# Bullets, dividers, and other decorative glyphs resume templates use around headings.
_DECORATIVE_CHARS = re.compile(r"[•▪■◆★✦●♦►▶›»|*_~=\[\]]+")
_LEADING_NUMBERING = re.compile(r"^(\d+[.)]|[ivxIVX]+[.)])\s*")


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


def _normalize_heading_candidate(first_line: str) -> str:
    """Normalize a candidate heading line for matching against known keywords.

    Handles the formatting quirks real resume templates use around section
    headings: decorative bullet/divider glyphs, numbering ("1. Experience"),
    letter-spaced all-caps ("E X P E R I E N C E"), and trailing punctuation.
    """
    text = _LEADING_NUMBERING.sub("", first_line.strip())
    # Collapse letter-spaced words ("E X P E R I E N C E" -> "EXPERIENCE") while
    # preserving real word boundaries: split on runs of 2+ spaces first (those
    # are genuine word gaps), then collapse single-letter tokens within each
    # remaining chunk.
    chunks = re.split(r"(\s{2,})", text)
    collapsed = []
    for chunk in chunks:
        if re.fullmatch(r"\s{2,}", chunk):
            collapsed.append(" ")
            continue
        tokens = chunk.split()
        if len(tokens) >= 2 and all(len(t) == 1 for t in tokens):
            collapsed.append("".join(tokens))
        else:
            collapsed.append(chunk)
    text = "".join(collapsed)
    text = _DECORATIVE_CHARS.sub(" ", text)
    text = re.sub(r"[:\-–—]+$", "", text.strip())
    return re.sub(r"\s+", " ", text).strip().lower()


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
    normalized = _normalize_heading_candidate(first_line)
    if not normalized:
        return None
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
        try:
            return ParsedResume(
                source_filename=os.path.basename(path),
                page_count=doc.page_count,
                sections=sections,
            )
        except pydantic.ValidationError as exc:
            present = {s.section_type for s in sections}
            found = [t.value for t in present]
            missing = [t.value for t in REQUIRED_SECTION_TYPES if t not in present]
            if not missing:
                raise  # a validation error we don't recognize; don't mask it
            raise MissingResumeSectionError(path, found, missing) from exc
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
