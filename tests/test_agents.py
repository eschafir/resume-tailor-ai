"""Unit tests for Phase 2 & 3 agents: prompt plumbing + schema validation
against a fake DeepSeek client (no live API calls, fully deterministic)."""

from __future__ import annotations

from resume_tailor.agents.job_profiler import profile_job
from resume_tailor.agents.recruiter_evaluator import evaluate_gap
from resume_tailor.agents.resume_profiler import profile_resume
from resume_tailor.agents.tailoring import tailor_bullets
from resume_tailor.agents.verification import verify_tailored_resume
from resume_tailor.schemas.candidate import BulletPoint, CandidateProfile, ExperienceEntry
from resume_tailor.schemas.evaluation import DeltaReport, OptimizationDirective
from resume_tailor.schemas.job import ExtractionMethod, JobSourceType, RawJobPosting
from resume_tailor.schemas.job_profile import JobProfile, SeniorityTier
from resume_tailor.schemas.tailoring import TailoredBullet, TailoredResume
from resume_tailor.schemas.verification import BulletVerification, VerificationReport
from tests.fakes import FakeDeepSeekClient
from tests.fixtures import generate_pdfs


def test_job_profiler_entity_extraction():
    posting = RawJobPosting(
        source_type=JobSourceType.PDF,
        source="sample_job.pdf",
        raw_text="\n\n".join(generate_pdfs.JOB_BODY_PARAGRAPHS) + "x" * 100,
        extraction_method=ExtractionMethod.PDF_TEXT,
        fetched_at="2026-01-01T00:00:00Z",
    )
    expected_profile = JobProfile(
        title=generate_pdfs.JOB_TITLE,
        company=generate_pdfs.JOB_COMPANY,
        role_summary="Senior Backend Engineer on the Platform team.",
        required_qualifications=[
            "5+ years of backend experience",
            "Strong Python or Go skills",
            "Experience with Kubernetes",
        ],
        preferred_qualifications=[
            "Experience with event-driven architectures",
            "PostgreSQL experience",
            "Mentoring junior engineers",
        ],
        tech_stack=["Python", "Go", "Kubernetes", "PostgreSQL"],
        seniority=SeniorityTier.SENIOR,
        keyword_index=["Python", "Go", "Kubernetes", "PostgreSQL", "backend", "distributed systems"],
    )
    fake_client = FakeDeepSeekClient(expected_profile)

    result = profile_job(posting, client=fake_client)

    assert result == expected_profile
    assert "5+ years" in result.required_qualifications[0]
    assert "Kubernetes" in result.tech_stack

    # Plumbing: the job posting's actual text reached the model as the user turn.
    sent_kwargs = fake_client.calls[0]
    system_msg, user_msg = sent_kwargs["messages"]
    assert generate_pdfs.JOB_BODY_PARAGRAPHS[2] in user_msg["content"]
    assert sent_kwargs["response_format"] == {"type": "json_object"}
    assert "required_qualifications" in system_msg["content"]  # schema embedded in the prompt


def test_resume_profiler_bullet_decomposition(resume_pdf_path):
    from resume_tailor.ingestion.pdf_parser import parse_resume_pdf

    parsed = parse_resume_pdf(resume_pdf_path)

    expected_bullet = BulletPoint(
        text="Led migration of the payments service to a distributed event-driven architecture, "
        "reducing p99 latency by 30%.",
        action_verb="Led",
        tools=["event-driven architecture"],
        metrics=["30%"],
    )
    expected_profile = CandidateProfile(
        full_name=generate_pdfs.CONTACT_NAME,
        contact_summary=generate_pdfs.CONTACT_LINE,
        experience=[
            ExperienceEntry(
                company="Acme Corp",
                title="Senior Software Engineer",
                start_date="2020",
                end_date="2024",
                bullets=[expected_bullet],
            )
        ],
        hard_skills=["Python", "Go", "Kubernetes"],
    )
    fake_client = FakeDeepSeekClient(expected_profile)

    result = profile_resume(parsed, client=fake_client)

    assert result == expected_profile
    bullet = result.experience[0].bullets[0]
    assert bullet.action_verb == "Led"
    assert "30%" in bullet.metrics

    # Plumbing: section-labeled resume text reached the model as the user turn.
    sent_kwargs = fake_client.calls[0]
    system_msg, user_msg = sent_kwargs["messages"]
    assert "## experience" in user_msg["content"]
    assert "Led migration of the payments service" in user_msg["content"]
    assert sent_kwargs["response_format"] == {"type": "json_object"}


def test_recruiter_agent_gap_identification():
    job_profile = JobProfile(
        title="Senior Backend Engineer",
        role_summary="Backend role requiring Python and Kubernetes.",
        required_qualifications=["Strong Python skills", "Experience with Kubernetes"],
        tech_stack=["Python", "Kubernetes"],
        keyword_index=["Python", "Kubernetes"],
    )
    candidate_profile = CandidateProfile(
        full_name="Jane Doe",
        hard_skills=["Python", "AWS"],
    )
    expected_report = DeltaReport(
        fit_score=55,
        matched_qualifications=["Strong Python skills"],
        missing_keywords=["Kubernetes"],
        keyword_alignment_map={"Python": "Python"},
        recommendations=[
            OptimizationDirective(
                target="Skills section",
                instruction="Add Kubernetes if the candidate has any container-orchestration experience.",
            )
        ],
    )
    fake_client = FakeDeepSeekClient(expected_report)

    result = evaluate_gap(job_profile, candidate_profile, client=fake_client)

    assert result == expected_report
    assert "Kubernetes" in result.missing_keywords
    assert "Strong Python skills" in result.matched_qualifications

    # Plumbing: both profiles' real content reached the model as the user turn.
    sent_kwargs = fake_client.calls[0]
    system_msg, user_msg = sent_kwargs["messages"]
    assert "Kubernetes" in user_msg["content"]
    assert "Jane Doe" in user_msg["content"]
    assert sent_kwargs["response_format"] == {"type": "json_object"}


def test_tailoring_agent_keyword_alignment_plumbing():
    candidate_profile = CandidateProfile(
        full_name="Jane Doe",
        experience=[
            ExperienceEntry(
                company="Acme Corp",
                title="Software Engineer",
                bullets=[
                    BulletPoint(text="Built an internal deployment pipeline.", action_verb="Built")
                ],
            )
        ],
    )
    delta_report = DeltaReport(fit_score=60, missing_keywords=["Kubernetes"])
    expected_result = TailoredResume(
        tailored_bullets=[
            TailoredBullet(
                company="Acme Corp",
                original_text="Built an internal deployment pipeline.",
                tailored_text="Built an internal deployment pipeline running on Kubernetes.",
                keywords_incorporated=["Kubernetes"],
            )
        ]
    )
    fake_client = FakeDeepSeekClient(expected_result)

    result = tailor_bullets(candidate_profile, delta_report, client=fake_client)

    assert result == expected_result
    assert "Kubernetes" in result.tailored_bullets[0].tailored_text

    # Plumbing: candidate profile and delta report content reached the model.
    sent_kwargs = fake_client.calls[0]
    system_msg, user_msg = sent_kwargs["messages"]
    assert "Built an internal deployment pipeline." in user_msg["content"]
    assert "Kubernetes" in user_msg["content"]
    assert sent_kwargs["response_format"] == {"type": "json_object"}


def test_tailoring_agent_includes_regeneration_feedback_plumbing():
    candidate_profile = CandidateProfile(full_name="Jane Doe")
    delta_report = DeltaReport(fit_score=60)
    feedback = VerificationReport(
        bullet_verifications=[
            BulletVerification(
                tailored_text="Reduced latency by 90% using Rust.",
                entailment_score=0.2,
                passed=False,
                issues=["'90%' not present in original", "'Rust' not present in original"],
            )
        ]
    )
    expected_result = TailoredResume(tailored_bullets=[])
    fake_client = FakeDeepSeekClient(expected_result)

    tailor_bullets(candidate_profile, delta_report, feedback=feedback, client=fake_client)

    sent_kwargs = fake_client.calls[0]
    _, user_msg = sent_kwargs["messages"]
    assert "Regeneration required" in user_msg["content"]
    assert "90%" in user_msg["content"]
    assert "Rust" in user_msg["content"]


def test_verification_agent_plumbing():
    tailored_resume = TailoredResume(
        tailored_bullets=[
            TailoredBullet(
                company="Acme Corp",
                original_text="Led a team of 4 engineers.",
                tailored_text="Led a cross-functional team of 4 engineers.",
                keywords_incorporated=[],
            )
        ]
    )
    expected_report = VerificationReport(
        bullet_verifications=[
            BulletVerification(
                tailored_text="Led a cross-functional team of 4 engineers.",
                entailment_score=0.95,
                passed=True,
                issues=[],
            )
        ]
    )
    fake_client = FakeDeepSeekClient(expected_report)

    result = verify_tailored_resume(tailored_resume, client=fake_client)

    assert result == expected_report
    assert result.all_passed is True

    # Plumbing: both the original and tailored bullet text reached the model.
    sent_kwargs = fake_client.calls[0]
    system_msg, user_msg = sent_kwargs["messages"]
    assert "Led a team of 4 engineers." in user_msg["content"]
    assert "Led a cross-functional team of 4 engineers." in user_msg["content"]
    assert sent_kwargs["response_format"] == {"type": "json_object"}


def test_verification_report_all_passed_is_derived_not_model_reported():
    report = VerificationReport(
        bullet_verifications=[
            BulletVerification(tailored_text="a", entailment_score=1.0, passed=True, issues=[]),
            BulletVerification(tailored_text="b", entailment_score=0.1, passed=False, issues=["bad"]),
        ]
    )
    assert report.all_passed is False
