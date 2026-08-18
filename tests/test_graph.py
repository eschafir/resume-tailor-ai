"""Tests for the LangGraph pipeline wiring, including the verification retry loop."""

from __future__ import annotations

from unittest.mock import patch

from resume_tailor.graph.build import MAX_TAILORING_ATTEMPTS, build_graph
from resume_tailor.schemas.candidate import CandidateProfile
from resume_tailor.schemas.evaluation import DeltaReport
from resume_tailor.schemas.job import ExtractionMethod, JobSourceType, RawJobPosting
from resume_tailor.schemas.job_profile import JobProfile
from resume_tailor.schemas.tailoring import TailoredBullet, TailoredResume
from resume_tailor.schemas.verification import BulletVerification, VerificationReport
from tests.fixtures import generate_pdfs


def _job_posting() -> RawJobPosting:
    return RawJobPosting(
        source_type=JobSourceType.PDF,
        source="sample_job.pdf",
        raw_text="\n\n".join(generate_pdfs.JOB_BODY_PARAGRAPHS) + "x" * 100,
        extraction_method=ExtractionMethod.PDF_TEXT,
        fetched_at="2026-01-01T00:00:00Z",
    )


def test_graph_compiles():
    graph = build_graph()
    assert graph is not None


def test_graph_pipeline_orchestrates_agents(resume_pdf_path):
    from resume_tailor.ingestion.pdf_parser import parse_resume_pdf

    parsed_resume = parse_resume_pdf(resume_pdf_path)

    fake_job_profile = JobProfile(title="Senior Backend Engineer", role_summary="...")
    fake_candidate_profile = CandidateProfile(full_name="Jane Doe")
    fake_delta_report = DeltaReport(fit_score=70)
    fake_tailored_resume = TailoredResume(
        tailored_bullets=[
            TailoredBullet(company="Acme Corp", original_text="did stuff", tailored_text="Did stuff")
        ]
    )
    fake_verification_report = VerificationReport(
        bullet_verifications=[
            BulletVerification(tailored_text="Did stuff", entailment_score=1.0, passed=True)
        ]
    )

    with (
        patch("resume_tailor.graph.build.profile_job", return_value=fake_job_profile) as mock_job,
        patch(
            "resume_tailor.graph.build.profile_resume", return_value=fake_candidate_profile
        ) as mock_resume,
        patch("resume_tailor.graph.build.evaluate_gap", return_value=fake_delta_report) as mock_eval,
        patch(
            "resume_tailor.graph.build.tailor_bullets", return_value=fake_tailored_resume
        ) as mock_tailor,
        patch(
            "resume_tailor.graph.build.verify_tailored_resume",
            return_value=fake_verification_report,
        ) as mock_verify,
    ):
        graph = build_graph()
        result = graph.invoke({"job_posting": _job_posting(), "parsed_resume": parsed_resume})

    mock_job.assert_called_once()
    mock_resume.assert_called_once()
    mock_eval.assert_called_once_with(fake_job_profile, fake_candidate_profile)
    mock_tailor.assert_called_once()
    mock_verify.assert_called_once_with(fake_tailored_resume)

    assert result["job_profile"] == fake_job_profile
    assert result["candidate_profile"] == fake_candidate_profile
    assert result["delta_report"] == fake_delta_report
    assert result["tailored_resume"] == fake_tailored_resume
    assert result["verification_report"] == fake_verification_report
    assert result["tailoring_attempts"] == 1


def test_graph_retries_tailoring_on_failed_verification(resume_pdf_path):
    """A failed verification should route back to tailoring, not straight to END."""
    from resume_tailor.ingestion.pdf_parser import parse_resume_pdf

    parsed_resume = parse_resume_pdf(resume_pdf_path)

    fake_job_profile = JobProfile(title="Senior Backend Engineer", role_summary="...")
    fake_candidate_profile = CandidateProfile(full_name="Jane Doe")
    fake_delta_report = DeltaReport(fit_score=70)
    fake_tailored_resume = TailoredResume(
        tailored_bullets=[
            TailoredBullet(
                company="Acme Corp", original_text="did stuff", tailored_text="Did amazing stuff"
            )
        ]
    )
    failing_report = VerificationReport(
        bullet_verifications=[
            BulletVerification(
                tailored_text="Did amazing stuff",
                entailment_score=0.1,
                passed=False,
                issues=["fabricated claim"],
            )
        ]
    )

    with (
        patch("resume_tailor.graph.build.profile_job", return_value=fake_job_profile),
        patch("resume_tailor.graph.build.profile_resume", return_value=fake_candidate_profile),
        patch("resume_tailor.graph.build.evaluate_gap", return_value=fake_delta_report),
        patch(
            "resume_tailor.graph.build.tailor_bullets", return_value=fake_tailored_resume
        ) as mock_tailor,
        # Verification always fails, so the graph should retry up to MAX_TAILORING_ATTEMPTS.
        patch(
            "resume_tailor.graph.build.verify_tailored_resume", return_value=failing_report
        ) as mock_verify,
    ):
        graph = build_graph()
        result = graph.invoke({"job_posting": _job_posting(), "parsed_resume": parsed_resume})

    assert mock_tailor.call_count == MAX_TAILORING_ATTEMPTS
    assert mock_verify.call_count == MAX_TAILORING_ATTEMPTS
    assert result["tailoring_attempts"] == MAX_TAILORING_ATTEMPTS
    assert result["verification_report"].all_passed is False

    # The second (and later) tailoring calls must carry the prior failure as feedback.
    second_call_kwargs = mock_tailor.call_args_list[1].kwargs
    assert second_call_kwargs["feedback"] == failing_report
