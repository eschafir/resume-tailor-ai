"""Tests for Phase 4: document generation & ATS typesetting."""

from __future__ import annotations

import pymupdf
import pytest

from resume_tailor.document.build_renderable import build_renderable_resume
from resume_tailor.document.diff import generate_diff
from resume_tailor.document.typesetting import compile_resume_pdf
from resume_tailor.errors import DocumentCompilationError
from resume_tailor.schemas.candidate import (
    BulletPoint,
    CandidateProfile,
    EducationEntry,
    ExperienceEntry,
    ProjectEntry,
)
from resume_tailor.schemas.diff import DiffStatus
from resume_tailor.schemas.tailoring import TailoredBullet, TailoredResume


def _sample_candidate() -> CandidateProfile:
    return CandidateProfile(
        full_name="Jane Doe",
        contact_summary="jane.doe@example.com | San Francisco, CA",
        experience=[
            ExperienceEntry(
                company="Acme Corp",
                title="Senior Software Engineer",
                start_date="2020",
                end_date="2024",
                bullets=[
                    BulletPoint(text="Led migration of the payments service.", action_verb="Led"),
                    BulletPoint(text="Mentored 4 junior engineers.", action_verb="Mentored"),
                ],
            )
        ],
        education=[
            EducationEntry(
                institution="State University", degree="B.S. Computer Science", graduation_date="2016"
            )
        ],
        hard_skills=["Python", "Go"],
        soft_skills=["Leadership"],
        projects=[
            ProjectEntry(
                name="Open Source Contributor, httpx",
                bullets=[BulletPoint(text="Fixed a connection-pool race condition.", action_verb="Fixed")],
            )
        ],
    )


def _sample_tailored() -> TailoredResume:
    return TailoredResume(
        tailored_summary="Backend engineer specializing in distributed systems and Kubernetes.",
        tailored_bullets=[
            TailoredBullet(
                company="Acme Corp",
                original_text="Led migration of the payments service.",
                tailored_text="Led migration of the payments service to a Kubernetes-orchestrated platform.",
                keywords_incorporated=["Kubernetes"],
            ),
            TailoredBullet(
                company="Acme Corp",
                original_text="Mentored 4 junior engineers.",
                tailored_text="Mentored 4 junior engineers.",
                keywords_incorporated=[],
            ),
        ],
    )


def test_pdf_compilation_success(tmp_path):
    renderable = build_renderable_resume(_sample_candidate(), _sample_tailored())

    output_path = tmp_path / "resume.pdf"
    compile_resume_pdf(renderable, str(output_path))

    assert output_path.exists()
    assert output_path.stat().st_size > 0

    doc = pymupdf.open(str(output_path))
    assert 1 <= doc.page_count <= 2


def test_pdf_compilation_failure_raises_typed_error(tmp_path, monkeypatch):
    import resume_tailor.document.typesetting as typesetting_module

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated typst failure")

    monkeypatch.setattr(typesetting_module.typst, "compile", _boom)

    renderable = build_renderable_resume(_sample_candidate(), _sample_tailored())
    with pytest.raises(DocumentCompilationError):
        compile_resume_pdf(renderable, str(tmp_path / "resume.pdf"))


def test_pdf_text_extractability(tmp_path):
    renderable = build_renderable_resume(_sample_candidate(), _sample_tailored())

    output_path = tmp_path / "resume.pdf"
    compile_resume_pdf(renderable, str(output_path))

    doc = pymupdf.open(str(output_path))
    full_text = "\n".join(page.get_text() for page in doc)
    upper_text = full_text.upper()

    # All tailored sections are present and machine-readable.
    assert "Jane Doe" in full_text
    assert "SUMMARY" in upper_text
    assert "EXPERIENCE" in upper_text
    assert "EDUCATION" in upper_text
    assert "SKILLS" in upper_text
    assert "PROJECTS" in upper_text
    # The tailored (not original) bullet text appears.
    assert "Kubernetes-orchestrated platform" in full_text

    # Sections appear in standard resume order.
    name_idx = full_text.find("Jane Doe")
    experience_idx = upper_text.find("EXPERIENCE")
    education_idx = upper_text.find("EDUCATION")
    skills_idx = upper_text.find("SKILLS")
    assert name_idx < experience_idx < education_idx < skills_idx


def test_diff_generator_accuracy():
    candidate = _sample_candidate()
    tailored = TailoredResume(
        tailored_bullets=[
            # Changed: tailored text differs from the original bullet.
            TailoredBullet(
                company="Acme Corp",
                original_text="Led migration of the payments service.",
                tailored_text="Led migration of the payments service to a Kubernetes-orchestrated platform.",
            ),
            # Unchanged: tailored text is identical to the original.
            TailoredBullet(
                company="Acme Corp",
                original_text="Mentored 4 junior engineers.",
                tailored_text="Mentored 4 junior engineers.",
            ),
            # Added: original_text doesn't match any bullet in the candidate profile.
            TailoredBullet(
                company="Acme Corp",
                original_text="Won an internal hackathon.",
                tailored_text="Won an internal hackathon.",
            ),
        ]
    )

    diff = generate_diff(candidate, tailored)
    by_tailored_text = {d.tailored_text: d for d in diff.bullets}

    changed = by_tailored_text[
        "Led migration of the payments service to a Kubernetes-orchestrated platform."
    ]
    assert changed.status == DiffStatus.CHANGED
    assert changed.original_text == "Led migration of the payments service."

    unchanged = by_tailored_text["Mentored 4 junior engineers."]
    assert unchanged.status == DiffStatus.UNCHANGED

    added = by_tailored_text["Won an internal hackathon."]
    assert added.status == DiffStatus.ADDED
    assert added.original_text is None

    # The candidate's untouched Projects bullet also carries through as unchanged.
    project_bullet = by_tailored_text["Fixed a connection-pool race condition."]
    assert project_bullet.status == DiffStatus.UNCHANGED
    assert project_bullet.company == "Open Source Contributor, httpx"
