"""Live-model integration tests for Phase 2 & 3 agents.

These call the real DeepSeek API and are skipped automatically when no
credentials are configured, so the default `pytest` run stays hermetic, fast,
and free. Set DEEPSEEK_API_KEY (e.g. in .env) to validate real
entity-extraction and anti-hallucination accuracy.

Phase 3 tests build small, deliberate inputs (rather than depending on
whatever a full pipeline run happens to produce) so each test isolates one
specific behavior: does a truthful keyword surface naturally, does an
injected fabrication get caught, does a faithful paraphrase pass.
"""

from __future__ import annotations

import os

import pytest

from resume_tailor.agents.job_profiler import profile_job
from resume_tailor.agents.recruiter_evaluator import evaluate_gap
from resume_tailor.agents.resume_profiler import profile_resume
from resume_tailor.agents.tailoring import tailor_bullets
from resume_tailor.agents.verification import verify_tailored_resume
from resume_tailor.ingestion.pdf_parser import parse_job_pdf, parse_resume_pdf
from resume_tailor.schemas.candidate import BulletPoint, CandidateProfile, ExperienceEntry
from resume_tailor.schemas.evaluation import DeltaReport, OptimizationDirective
from resume_tailor.schemas.tailoring import TailoredBullet, TailoredResume

_HAS_CREDENTIALS = bool(os.environ.get("DEEPSEEK_API_KEY"))

pytestmark = pytest.mark.skipif(
    not _HAS_CREDENTIALS,
    reason="requires a live DeepSeek API key (DEEPSEEK_API_KEY)",
)


def test_job_profiler_entity_extraction_live(job_pdf_path):
    posting = parse_job_pdf(job_pdf_path)

    profile = profile_job(posting)

    keywords = {k.lower() for k in profile.keyword_index + profile.tech_stack}
    assert "kubernetes" in keywords
    assert any("5" in q and "year" in q.lower() for q in profile.required_qualifications)


def test_resume_profiler_bullet_decomposition_live(resume_pdf_path):
    parsed = parse_resume_pdf(resume_pdf_path)

    profile = profile_resume(parsed)

    all_bullets = [b for entry in profile.experience for b in entry.bullets]
    assert all_bullets, "expected at least one decomposed bullet"
    assert any("30%" in b.metrics for b in all_bullets)
    assert any(b.action_verb.lower() == "led" for b in all_bullets)


def test_recruiter_agent_gap_identification_live(job_pdf_path, resume_pdf_path):
    job_profile = profile_job(parse_job_pdf(job_pdf_path))
    candidate_profile = profile_resume(parse_resume_pdf(resume_pdf_path))

    report = evaluate_gap(job_profile, candidate_profile)

    assert 0 <= report.fit_score <= 100
    assert report.matched_qualifications or report.missing_keywords


def test_tailoring_agent_keyword_alignment():
    candidate_profile = CandidateProfile(
        full_name="Jane Doe",
        experience=[
            ExperienceEntry(
                company="Acme Corp",
                title="Backend Engineer",
                bullets=[
                    BulletPoint(
                        text="Built and maintained a containerized deployment pipeline "
                        "for internal services.",
                        action_verb="Built",
                    )
                ],
            )
        ],
    )
    delta_report = DeltaReport(
        fit_score=60,
        missing_keywords=["Kubernetes"],
        recommendations=[
            OptimizationDirective(
                target="Acme Corp deployment pipeline bullet",
                instruction="Mention Kubernetes, since the pipeline was already containerized.",
            )
        ],
    )

    result = tailor_bullets(candidate_profile, delta_report)

    tailored_text = " ".join(b.tailored_text for b in result.tailored_bullets).lower()
    assert "kubernetes" in tailored_text


def test_verification_agent_detects_hallucinations():
    tailored_resume = TailoredResume(
        tailored_bullets=[
            TailoredBullet(
                company="Acme Corp",
                original_text="Improved API response times through caching.",
                tailored_text=(
                    "Improved API response times by 47% by migrating to a custom "
                    "Rust-based caching layer."
                ),
                keywords_incorporated=["Rust"],
            )
        ]
    )

    report = verify_tailored_resume(tailored_resume)

    assert len(report.bullet_verifications) == 1
    verification = report.bullet_verifications[0]
    assert verification.passed is False
    assert verification.entailment_score < 0.8
    assert verification.issues
    assert report.all_passed is False


def test_verification_agent_passes_faithful_paraphrase():
    from tests.fixtures import generate_pdfs

    original = generate_pdfs.EXPERIENCE_ENTRIES[0][1][0]
    tailored_resume = TailoredResume(
        tailored_bullets=[
            TailoredBullet(
                company="Acme Corp",
                original_text=original,
                tailored_text=(
                    "Spearheaded the migration of the payments platform to a "
                    "distributed, event-driven architecture, cutting p99 latency by 30%."
                ),
                keywords_incorporated=["event-driven", "distributed"],
            )
        ]
    )

    report = verify_tailored_resume(tailored_resume)

    verification = report.bullet_verifications[0]
    assert verification.passed is True
    assert verification.entailment_score >= 0.8
    assert report.all_passed is True
