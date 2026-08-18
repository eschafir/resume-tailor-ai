"""Command-line entry point (Phase 5).

    resume-tailor --resume resume.pdf --job-url https://example.com/job/123
    resume-tailor --resume resume.pdf --job-pdf job.pdf --output tailored.pdf
"""

from __future__ import annotations

import argparse
import sys

from resume_tailor.errors import (
    CorruptPDFError,
    DocumentCompilationError,
    HTTPFetchError,
    InsufficientContentError,
    InvalidURLError,
    LLMResponseError,
    MissingResumeSectionError,
)
from resume_tailor.orchestrator import run_pipeline

_PIPELINE_ERRORS = (
    CorruptPDFError,
    InvalidURLError,
    HTTPFetchError,
    InsufficientContentError,
    LLMResponseError,
    MissingResumeSectionError,
    DocumentCompilationError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resume-tailor",
        description="Generate an ATS-friendly, verified, job-tailored resume PDF.",
    )
    parser.add_argument("--resume", required=True, help="Path to your resume PDF")
    job_group = parser.add_mutually_exclusive_group(required=True)
    job_group.add_argument("--job-pdf", help="Path to the target job posting PDF")
    job_group.add_argument("--job-url", help="URL of the target job posting")
    parser.add_argument(
        "--output", default="tailored_resume.pdf", help="Where to write the tailored PDF"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = run_pipeline(
            resume_pdf_path=args.resume,
            job_pdf_path=args.job_pdf,
            job_url=args.job_url,
            output_pdf_path=args.output,
        )
    except _PIPELINE_ERRORS as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Fit score: {result.delta_report.fit_score}/100")
    status = "PASSED" if result.verification_report.all_passed else "FAILED (max retries reached)"
    print(f"Anti-hallucination verification: {status}")
    print(f"Tailored resume written to: {result.output_pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
