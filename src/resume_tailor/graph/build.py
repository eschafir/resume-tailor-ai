"""LangGraph wiring for the resume-tailoring pipeline.

    START ─┬─> job_profiler ────┐
           └─> resume_profiler ─┴─> evaluator ─> tailoring ─> verification ─┐
                                                       ^                    │
                                                       └──── retry ─────────┤
                                                                            v
                                                                          done -> END

Verification failures route back to tailoring with the failing bullets'
issues attached, bounded by MAX_TAILORING_ATTEMPTS so a persistently
hallucinating rewrite can't loop forever.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from resume_tailor.agents.job_profiler import profile_job
from resume_tailor.agents.recruiter_evaluator import evaluate_gap
from resume_tailor.agents.resume_profiler import profile_resume
from resume_tailor.agents.tailoring import tailor_bullets
from resume_tailor.agents.verification import verify_tailored_resume
from resume_tailor.graph.state import PipelineState

MAX_TAILORING_ATTEMPTS = 3


def job_profiler_node(state: PipelineState) -> dict:
    return {"job_profile": profile_job(state["job_posting"])}


def resume_profiler_node(state: PipelineState) -> dict:
    return {"candidate_profile": profile_resume(state["parsed_resume"])}


def evaluator_node(state: PipelineState) -> dict:
    delta_report = evaluate_gap(state["job_profile"], state["candidate_profile"])
    return {"delta_report": delta_report}


def tailoring_node(state: PipelineState) -> dict:
    attempts = state.get("tailoring_attempts", 0) + 1
    tailored_resume = tailor_bullets(
        state["candidate_profile"],
        state["delta_report"],
        feedback=state.get("verification_report"),
    )
    return {"tailored_resume": tailored_resume, "tailoring_attempts": attempts}


def verification_node(state: PipelineState) -> dict:
    verification_report = verify_tailored_resume(state["tailored_resume"])
    return {"verification_report": verification_report}


def route_after_verification(state: PipelineState) -> str:
    report = state["verification_report"]
    if report.all_passed:
        return "done"
    if state.get("tailoring_attempts", 0) >= MAX_TAILORING_ATTEMPTS:
        return "done"
    return "retry"


def build_graph() -> CompiledStateGraph:
    graph = StateGraph(PipelineState)
    graph.add_node("job_profiler", job_profiler_node)
    graph.add_node("resume_profiler", resume_profiler_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("tailoring", tailoring_node)
    graph.add_node("verification", verification_node)

    graph.add_edge(START, "job_profiler")
    graph.add_edge(START, "resume_profiler")
    graph.add_edge("job_profiler", "evaluator")
    graph.add_edge("resume_profiler", "evaluator")
    graph.add_edge("evaluator", "tailoring")
    graph.add_edge("tailoring", "verification")
    graph.add_conditional_edges(
        "verification",
        route_after_verification,
        {"retry": "tailoring", "done": END},
    )

    return graph.compile()
