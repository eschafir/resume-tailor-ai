"""LangGraph state schema for the profiler/evaluator/tailoring/verification pipeline."""

from __future__ import annotations

from typing import TypedDict

from typing_extensions import NotRequired

from resume_tailor.schemas.candidate import CandidateProfile
from resume_tailor.schemas.document import ParsedResume
from resume_tailor.schemas.evaluation import DeltaReport
from resume_tailor.schemas.job import RawJobPosting
from resume_tailor.schemas.job_profile import JobProfile
from resume_tailor.schemas.tailoring import TailoredResume
from resume_tailor.schemas.verification import VerificationReport


class PipelineState(TypedDict):
    job_posting: RawJobPosting
    parsed_resume: ParsedResume
    job_profile: NotRequired[JobProfile]
    candidate_profile: NotRequired[CandidateProfile]
    delta_report: NotRequired[DeltaReport]
    tailored_resume: NotRequired[TailoredResume]
    verification_report: NotRequired[VerificationReport]
    tailoring_attempts: NotRequired[int]
