"""Programmatically generates benchmark PDF fixtures for Phase 1 ingestion tests.

Building fixtures with PyMuPDF (rather than committing binary PDFs) keeps the
repo text-only and lets tests assert on exact known content.
"""

from __future__ import annotations

import pymupdf as fitz

_FONT = "helv"
_LINE_HEIGHT = 14
_SECTION_GAP = 26
_MARGIN_X = 50
_PAGE_WIDTH = 612
_PAGE_HEIGHT = 792


class _PageWriter:
    """Writes lines top-down onto a fresh page, wrapping to a new page when full."""

    def __init__(self, doc: fitz.Document) -> None:
        self._doc = doc
        self._page = doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        self._y = 60

    def _ensure_space(self, needed: float) -> None:
        if self._y + needed > _PAGE_HEIGHT - 50:
            self._page = self._doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
            self._y = 60

    def line(self, text: str, *, fontsize: float = 11, gap_before: float = 0) -> None:
        self._ensure_space(_LINE_HEIGHT + gap_before)
        self._y += gap_before
        self._page.insert_text((_MARGIN_X, self._y), text, fontsize=fontsize, fontname=_FONT)
        self._y += _LINE_HEIGHT

    def heading(self, text: str) -> None:
        self.line(text, fontsize=13, gap_before=_SECTION_GAP)


# Canonical content, also imported by tests so assertions don't hardcode strings twice.
CONTACT_NAME = "Jane Doe"
CONTACT_LINE = "jane.doe@example.com | (555) 123-4567 | San Francisco, CA"
SUMMARY_TEXT = "Backend engineer with 8 years building distributed systems at scale."
EXPERIENCE_ENTRIES = [
    (
        "Senior Software Engineer, Acme Corp (2020-2024)",
        [
            "Led migration of the payments service to a distributed event-driven architecture, reducing p99 latency by 30%.",
            "Mentored 4 junior engineers and established the team's code review standards.",
        ],
    ),
    (
        "Software Engineer, Beta Systems (2016-2020)",
        [
            "Built internal analytics pipeline processing 2TB of daily log data using Spark and Airflow.",
            "Shipped a self-service API gateway adopted by 12 downstream teams.",
        ],
    ),
]
EDUCATION_TEXT = "B.S. Computer Science, State University, 2016"
SKILLS_TEXT = "Python, Go, Kubernetes, AWS, PostgreSQL, Leadership, Technical Communication"
PROJECTS_ENTRIES = [
    (
        "Open Source Contributor, httpx",
        ["Fixed a connection-pool race condition affecting high-concurrency clients."],
    ),
]


def build_resume_pdf(path: str) -> None:
    doc = fitz.open()
    w = _PageWriter(doc)

    w.line(CONTACT_NAME, fontsize=16)
    w.line(CONTACT_LINE, fontsize=10)

    w.heading("Summary")
    w.line(SUMMARY_TEXT)

    w.heading("Experience")
    for title, bullets in EXPERIENCE_ENTRIES:
        w.line(title, fontsize=11, gap_before=10)
        for bullet in bullets:
            w.line(f"- {bullet}")

    w.heading("Education")
    w.line(EDUCATION_TEXT)

    w.heading("Skills")
    w.line(SKILLS_TEXT)

    w.heading("Projects")
    for title, bullets in PROJECTS_ENTRIES:
        w.line(title, fontsize=11, gap_before=10)
        for bullet in bullets:
            w.line(f"- {bullet}")

    doc.save(path)
    doc.close()


JOB_TITLE = "Senior Backend Engineer"
JOB_COMPANY = "Northwind Technologies"
JOB_BODY_PARAGRAPHS = [
    "Northwind Technologies is looking for a Senior Backend Engineer to join our Platform team.",
    "You will design and operate distributed systems that process millions of events per day.",
    "Requirements: 5+ years of backend experience, strong Python or Go skills, and experience with Kubernetes.",
    "Preferred: experience with event-driven architectures, PostgreSQL, and mentoring junior engineers.",
    "We offer competitive compensation, remote-friendly work, and a strong engineering culture focused on ownership.",
]


def build_job_pdf(path: str) -> None:
    doc = fitz.open()
    w = _PageWriter(doc)
    w.line(JOB_TITLE, fontsize=16)
    w.line(JOB_COMPANY, fontsize=12, gap_before=6)
    for paragraph in JOB_BODY_PARAGRAPHS:
        w.line(paragraph, gap_before=14)
    doc.save(path)
    doc.close()


def build_corrupt_pdf(path: str) -> None:
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4\nthis is not a valid pdf body\n%%EOF")


if __name__ == "__main__":
    build_resume_pdf("/tmp/sample_resume.pdf")
    build_job_pdf("/tmp/sample_job.pdf")
    print("done")
