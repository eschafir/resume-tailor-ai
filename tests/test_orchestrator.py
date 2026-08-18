"""Test for Phase 5: full end-to-end pipeline execution."""

from __future__ import annotations

from unittest.mock import patch

import pymupdf

from resume_tailor.orchestrator import run_pipeline
from resume_tailor.schemas.candidate import BulletPoint, CandidateProfile, ExperienceEntry
from resume_tailor.schemas.diff import DiffStatus
from resume_tailor.schemas.evaluation import DeltaReport
from resume_tailor.schemas.job_profile import JobProfile
from resume_tailor.schemas.tailoring import TailoredBullet, TailoredResume
from resume_tailor.schemas.verification import BulletVerification, VerificationReport
from tests.fixtures import generate_pdfs


def test_end_to_end_pipeline_execution(resume_pdf_path, job_pdf_path, tmp_path):
    """Real ingestion + real PDF compilation, with the LLM agent calls mocked
    out (hermetic, deterministic) — verifies exit status and output integrity."""
    fake_job_profile = JobProfile(title="Senior Backend Engineer", role_summary="...")
    fake_candidate_profile = CandidateProfile(
        full_name=generate_pdfs.CONTACT_NAME,
        experience=[
            ExperienceEntry(
                company="Acme Corp",
                title="Senior Software Engineer",
                bullets=[BulletPoint(text="Led migration of the payments service.", action_verb="Led")],
            )
        ],
    )
    fake_delta_report = DeltaReport(fit_score=82, matched_qualifications=["Python"])
    fake_tailored_resume = TailoredResume(
        tailored_summary="A great engineer.",
        tailored_bullets=[
            TailoredBullet(
                company="Acme Corp",
                original_text="Led migration of the payments service.",
                tailored_text="Led migration of the payments service onto Kubernetes.",
            )
        ],
    )
    fake_verification_report = VerificationReport(
        bullet_verifications=[
            BulletVerification(
                tailored_text="Led migration of the payments service onto Kubernetes.",
                entailment_score=0.95,
                passed=True,
            )
        ]
    )

    output_path = tmp_path / "tailored_resume.pdf"

    with (
        patch("resume_tailor.graph.build.profile_job", return_value=fake_job_profile),
        patch("resume_tailor.graph.build.profile_resume", return_value=fake_candidate_profile),
        patch("resume_tailor.graph.build.evaluate_gap", return_value=fake_delta_report),
        patch("resume_tailor.graph.build.tailor_bullets", return_value=fake_tailored_resume),
        patch(
            "resume_tailor.graph.build.verify_tailored_resume",
            return_value=fake_verification_report,
        ),
    ):
        result = run_pipeline(
            resume_pdf_path=resume_pdf_path,
            job_pdf_path=job_pdf_path,
            output_pdf_path=str(output_path),
        )

    # "Exit status": the call completed and returned the expected reports.
    assert result.delta_report == fake_delta_report
    assert result.verification_report.all_passed is True
    assert result.output_pdf_path == str(output_path)

    # "Output integrity": a real, readable, correctly-populated PDF exists on disk.
    assert output_path.exists()
    doc = pymupdf.open(str(output_path))
    assert doc.page_count >= 1
    text = doc[0].get_text()
    assert generate_pdfs.CONTACT_NAME in text
    assert "Led migration of the payments service onto Kubernetes." in text

    # The diff correctly categorizes the one changed bullet.
    assert len(result.resume_diff.bullets) == 1
    assert result.resume_diff.bullets[0].status == DiffStatus.CHANGED
