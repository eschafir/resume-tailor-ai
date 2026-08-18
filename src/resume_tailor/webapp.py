"""Interactive web UI (Phase 5) — run with `streamlit run app.py`.

Three stages, each gated behind a button so the user can inspect results
before spending more API calls: analyze fit -> tailor & verify -> review,
accept/reject/edit each bullet, and compile the final PDF.
"""

from __future__ import annotations

import os
import tempfile

import streamlit as st

from resume_tailor.agents.job_profiler import profile_job
from resume_tailor.agents.recruiter_evaluator import evaluate_gap
from resume_tailor.agents.resume_profiler import profile_resume
from resume_tailor.agents.tailoring import tailor_bullets
from resume_tailor.agents.verification import verify_tailored_resume
from resume_tailor.document.build_renderable import build_renderable_resume
from resume_tailor.document.typesetting import compile_resume_pdf
from resume_tailor.errors import (
    CorruptPDFError,
    DocumentCompilationError,
    HTTPFetchError,
    InsufficientContentError,
    InvalidURLError,
    LLMResponseError,
    MissingResumeSectionError,
)
from resume_tailor.graph.build import MAX_TAILORING_ATTEMPTS
from resume_tailor.ingestion.pdf_parser import parse_job_pdf, parse_resume_pdf
from resume_tailor.ingestion.web_scraper import scrape_job_url
from resume_tailor.schemas.tailoring import TailoredBullet, TailoredResume

_PIPELINE_ERRORS = (
    CorruptPDFError,
    InvalidURLError,
    HTTPFetchError,
    InsufficientContentError,
    LLMResponseError,
    MissingResumeSectionError,
    DocumentCompilationError,
)


def _save_upload(uploaded_file) -> str:
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def _run_tailoring_loop(candidate_profile, delta_report):
    feedback = None
    tailored = None
    verification = None
    for _ in range(MAX_TAILORING_ATTEMPTS):
        tailored = tailor_bullets(candidate_profile, delta_report, feedback=feedback)
        verification = verify_tailored_resume(tailored)
        if verification.all_passed:
            break
        feedback = verification
    return tailored, verification


def main() -> None:
    st.set_page_config(page_title="Resume Tailor AI", layout="wide")
    st.title("Resume Tailor AI")
    st.caption("Tailor your resume to a job posting, with anti-hallucination verification.")

    # --- Stage 1: inputs -------------------------------------------------
    st.header("1. Upload your resume and target job")
    resume_file = st.file_uploader("Resume (PDF)", type="pdf")

    job_mode = st.radio("Job posting source", ["URL", "PDF"], horizontal=True)
    job_url = st.text_input("Job posting URL") if job_mode == "URL" else None
    job_file = st.file_uploader("Job posting (PDF)", type="pdf") if job_mode == "PDF" else None

    can_analyze = bool(resume_file) and bool(job_url or job_file)
    if st.button("Analyze fit", disabled=not can_analyze):
        try:
            with st.spinner("Parsing and profiling..."):
                resume_path = _save_upload(resume_file)
                parsed_resume = parse_resume_pdf(resume_path)
                candidate_profile = profile_resume(parsed_resume)

                if job_file is not None:
                    job_posting = parse_job_pdf(_save_upload(job_file))
                else:
                    job_posting = scrape_job_url(job_url)
                job_profile = profile_job(job_posting)

                delta_report = evaluate_gap(job_profile, candidate_profile)
        except _PIPELINE_ERRORS as exc:
            st.error(f"Couldn't process your inputs: {exc}")
        else:
            st.session_state.candidate_profile = candidate_profile
            st.session_state.delta_report = delta_report
            # Clear any downstream state from a previous run.
            st.session_state.pop("tailored_resume", None)
            st.session_state.pop("verification_report", None)

    # --- Stage 2: recruiter evaluation -----------------------------------
    if "delta_report" in st.session_state:
        report = st.session_state.delta_report
        st.header("2. Recruiter Evaluation")
        st.metric("Fit score", f"{report.fit_score}/100")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Matched qualifications")
            if report.matched_qualifications:
                for q in report.matched_qualifications:
                    st.markdown(f"- ✅ {q}")
            else:
                st.caption("None identified.")
        with col2:
            st.subheader("Missing keywords")
            if report.missing_keywords:
                for k in report.missing_keywords:
                    st.markdown(f"- ⚠️ {k}")
            else:
                st.caption("None — strong keyword coverage.")

        if report.recommendations:
            st.subheader("Recommendations")
            for rec in report.recommendations:
                st.markdown(f"- **{rec.target}**: {rec.instruction}")

        if st.button("Tailor bullets"):
            try:
                with st.spinner("Tailoring and verifying against the source resume..."):
                    tailored, verification = _run_tailoring_loop(
                        st.session_state.candidate_profile, report
                    )
            except _PIPELINE_ERRORS as exc:
                st.error(f"Couldn't tailor your resume: {exc}")
            else:
                st.session_state.tailored_resume = tailored
                st.session_state.verification_report = verification

    # --- Stage 3: review, accept/reject/edit, compile ---------------------
    if "tailored_resume" in st.session_state:
        tailored: TailoredResume = st.session_state.tailored_resume
        verification = st.session_state.verification_report

        st.header("3. Review tailored bullets")
        if verification.all_passed:
            st.success("All bullets passed anti-hallucination verification.")
        else:
            st.warning(
                "Some bullets failed verification after "
                f"{MAX_TAILORING_ATTEMPTS} attempts and default to the original text below."
            )

        final_texts: dict[int, str] = {}
        for i, (bullet, v) in enumerate(zip(tailored.tailored_bullets, verification.bullet_verifications)):
            st.markdown(f"**{bullet.company}**")
            col1, col2 = st.columns(2)
            with col1:
                st.caption("Original")
                st.write(bullet.original_text)
            with col2:
                status = "✅ Passed" if v.passed else "❌ Failed verification"
                st.caption(f"Tailored — {status} (entailment {v.entailment_score:.2f})")
                st.write(bullet.tailored_text)
            if v.issues:
                st.warning("Issues found: " + "; ".join(v.issues))

            default_choice = "Tailored" if v.passed else "Original"
            choice = st.radio(
                "Use for the final resume",
                ["Tailored", "Original", "Edit"],
                index=["Tailored", "Original", "Edit"].index(default_choice),
                horizontal=True,
                key=f"choice_{i}",
            )
            if choice == "Edit":
                final_texts[i] = st.text_area(
                    "Edit this bullet",
                    value=bullet.tailored_text if v.passed else bullet.original_text,
                    key=f"edit_{i}",
                )
            elif choice == "Tailored":
                final_texts[i] = bullet.tailored_text
            else:
                final_texts[i] = bullet.original_text
            st.divider()

        if st.button("Compile final PDF"):
            final_bullets = [
                TailoredBullet(
                    company=b.company,
                    original_text=b.original_text,
                    tailored_text=final_texts.get(i, b.original_text),
                    keywords_incorporated=b.keywords_incorporated,
                )
                for i, b in enumerate(tailored.tailored_bullets)
            ]
            final_tailored = TailoredResume(
                tailored_summary=tailored.tailored_summary, tailored_bullets=final_bullets
            )
            try:
                renderable = build_renderable_resume(
                    st.session_state.candidate_profile, final_tailored
                )
                output_path = os.path.join(tempfile.mkdtemp(), "tailored_resume.pdf")
                compile_resume_pdf(renderable, output_path)
            except DocumentCompilationError as exc:
                st.error(f"PDF compilation failed: {exc}")
            else:
                with open(output_path, "rb") as f:
                    st.download_button(
                        "Download tailored resume PDF",
                        f,
                        file_name="tailored_resume.pdf",
                        mime="application/pdf",
                    )


if __name__ == "__main__":
    main()
