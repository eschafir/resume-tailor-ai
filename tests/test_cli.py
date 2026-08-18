"""Tests for the CLI entry point (Phase 5): argument parsing correctly
triggers the orchestrator, with proper exit codes."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from resume_tailor.cli import main
from resume_tailor.errors import InvalidURLError
from resume_tailor.orchestrator import PipelineResult
from resume_tailor.schemas.diff import ResumeDiff
from resume_tailor.schemas.evaluation import DeltaReport
from resume_tailor.schemas.verification import VerificationReport


def _fake_result(**overrides) -> PipelineResult:
    defaults = dict(
        delta_report=DeltaReport(fit_score=77),
        verification_report=VerificationReport(bullet_verifications=[]),
        resume_diff=ResumeDiff(bullets=[]),
        output_pdf_path="out.pdf",
    )
    defaults.update(overrides)
    return PipelineResult(**defaults)


def test_cli_or_api_route_handling_job_url(capsys):
    with patch("resume_tailor.cli.run_pipeline", return_value=_fake_result()) as mock_run:
        exit_code = main(
            ["--resume", "resume.pdf", "--job-url", "https://example.com/job", "--output", "out.pdf"]
        )

    assert exit_code == 0
    mock_run.assert_called_once_with(
        resume_pdf_path="resume.pdf",
        job_pdf_path=None,
        job_url="https://example.com/job",
        output_pdf_path="out.pdf",
    )
    captured = capsys.readouterr()
    assert "77/100" in captured.out
    assert "out.pdf" in captured.out


def test_cli_or_api_route_handling_job_pdf():
    with patch("resume_tailor.cli.run_pipeline", return_value=_fake_result()) as mock_run:
        exit_code = main(["--resume", "resume.pdf", "--job-pdf", "job.pdf"])

    assert exit_code == 0
    mock_run.assert_called_once_with(
        resume_pdf_path="resume.pdf",
        job_pdf_path="job.pdf",
        job_url=None,
        output_pdf_path="tailored_resume.pdf",
    )


def test_cli_rejects_both_job_pdf_and_job_url():
    with pytest.raises(SystemExit):
        main(["--resume", "resume.pdf", "--job-pdf", "job.pdf", "--job-url", "https://x"])


def test_cli_requires_a_job_source():
    with pytest.raises(SystemExit):
        main(["--resume", "resume.pdf"])


def test_cli_returns_error_exit_code_on_pipeline_failure(capsys):
    with patch(
        "resume_tailor.cli.run_pipeline",
        side_effect=InvalidURLError("bad-url", "must be http(s)"),
    ):
        exit_code = main(["--resume", "resume.pdf", "--job-url", "not-a-url"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Error" in captured.err
