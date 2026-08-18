"""End-to-end pipeline orchestration (Phase 5).

The single function a caller (CLI, web UI, or a test) needs: give it a
resume PDF and a job posting (PDF or URL), get back a verified, compiled
tailored resume PDF plus the intermediate reports.
"""

from __future__ import annotations

from dataclasses import dataclass

from resume_tailor.document.build_renderable import build_renderable_resume
from resume_tailor.document.diff import generate_diff
from resume_tailor.document.typesetting import compile_resume_pdf
from resume_tailor.graph.build import build_graph
from resume_tailor.ingestion.pdf_parser import parse_job_pdf, parse_resume_pdf
from resume_tailor.ingestion.web_scraper import scrape_job_url
from resume_tailor.schemas.diff import ResumeDiff
from resume_tailor.schemas.evaluation import DeltaReport
from resume_tailor.schemas.job import RawJobPosting
from resume_tailor.schemas.verification import VerificationReport


@dataclass
class PipelineResult:
    delta_report: DeltaReport
    verification_report: VerificationReport
    resume_diff: ResumeDiff
    output_pdf_path: str


def ingest_job(*, job_pdf_path: str | None = None, job_url: str | None = None) -> RawJobPosting:
    """Ingest the target job posting from exactly one of a PDF path or a URL."""
    if job_pdf_path and job_url:
        raise ValueError("Provide either a job PDF or a job URL, not both.")
    if job_pdf_path:
        return parse_job_pdf(job_pdf_path)
    if job_url:
        return scrape_job_url(job_url)
    raise ValueError("Provide a job PDF path or a job URL.")


def run_pipeline(
    *,
    resume_pdf_path: str,
    output_pdf_path: str,
    job_pdf_path: str | None = None,
    job_url: str | None = None,
) -> PipelineResult:
    """Run the full pipeline: ingest -> profile -> evaluate -> tailor -> verify -> compile."""
    job_posting = ingest_job(job_pdf_path=job_pdf_path, job_url=job_url)
    parsed_resume = parse_resume_pdf(resume_pdf_path)

    graph = build_graph()
    final_state = graph.invoke({"job_posting": job_posting, "parsed_resume": parsed_resume})

    candidate_profile = final_state["candidate_profile"]
    tailored_resume = final_state["tailored_resume"]

    resume_diff = generate_diff(candidate_profile, tailored_resume)
    renderable = build_renderable_resume(candidate_profile, tailored_resume)
    compile_resume_pdf(renderable, output_pdf_path)

    return PipelineResult(
        delta_report=final_state["delta_report"],
        verification_report=final_state["verification_report"],
        resume_diff=resume_diff,
        output_pdf_path=output_pdf_path,
    )
