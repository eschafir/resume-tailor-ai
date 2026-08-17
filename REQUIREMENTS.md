# Resume Tailor AI — Requirements

## Summary

Resume Tailor AI is an automated multi-agent system designed to take a candidate's resume (PDF) alongside a target job position (PDF or URL) and generate a customized, ATS-friendly resume tailored specifically to that role. 

The goal is to eliminate manual tailoring while strictly preventing LLM fact-fabrication. By utilizing harness engineering and specialized, modular agents (Profilers, Evaluator/Recruiter, Copywriter, and Grounding Critic), the system analyzes the target job, identifies experience gaps, optimizes bullet points using proven impact frameworks (STAR/XYZ), verifies claims against source history, and produces a compiled, ready-to-use document.

---

## Core Workflow & Agent Roles

The application processes input data through an orchestrated multi-agent pipeline:

*   **Ingestion & Scraping Pipeline:** Ingests the candidate's PDF resume and the target job description (via PDF upload or URL scraping) and converts them into layout-aware structured text.
*   **Job Profiler Agent:** Extracts required hard/soft skills, experience levels, qualification thresholds, and company context into a typed schema.
*   **Resume Profiler Agent:** Deconstructs the source resume into work history, verified skills, metrics, education, and impact achievements.
*   **Recruiter / Evaluator Agent:** Performs gap analysis between the resume and job requirements, scoring candidate fit and producing a strategic delta roadmap (what to highlight, rephrase, or de-emphasize).
*   **Tailoring / Copywriting Agent:** Rewrites resume bullet points to map directly onto job requirements using action-driven formulas (Google XYZ / STAR) and aligned terminology.
*   **Verification / Anti-Hallucination Agent:** Performs strict bidirectional entailment checks against the source resume to guarantee that no metrics, skills, tools, or roles are fabricated.
*   **Document Renderer:** Compiles the validated structured JSON into an ATS-compliant PDF using a programmatic typesetting engine (e.g., Typst, LaTeX, or WeasyPrint).

---

## What the System Keeps Track Of

*   **Candidate Profile:** Contact details, work experience records, education, categorized hard/soft skills, project entries, and source impact metrics.
*   **Target Job Profile:** Title, organization, role summary, mandatory requirements, preferred qualifications, keyword index, and domain/seniority tier.
*   **Evaluation Delta:** Fit score (0–100%), matched qualifications, missing keywords, keyword alignment map, and prioritized tailoring recommendations.
*   **Tailored Version:** Rewritten bullet points, targeted summary section, modified skill hierarchy, change log, and diff matrix between original and revised entries.
*   **Verification Report:** Entailment score per rewritten line, flagged discrepancies or unverified assertions, and pass/fail guardrail status.

---

## High-Level Technical Guidance

*   **Stack:** Python-based orchestrator (e.g., LangGraph, LlamaIndex Workflows, or FastAPI + custom state machine) with a clean web interface (React/TypeScript or Streamlit).
*   **Parsing:** Use layout-aware PDF parsers (e.g., Docling or PyMuPDF) rather than naive text extractors. For URLs, use headless scraping (Playwright or Crawl4AI) with fallback article extractors to bypass single-page app (SPA) rendering obstacles.
*   **Data Models:** Define strict Pydantic schemas for state transitions between agents to avoid passing unstructured text.
*   **Typesetting Engine:** Use deterministic markup-to-PDF compilers (Typst, LaTeX, or HTML/WeasyPrint) for clean ATS-friendly exports.
*   **Local & Containerized Execution:** Ensure the entire pipeline and its headless dependencies can run reliably via Docker or a local environment with a single startup command[cite: 1].

---

## Not in Scope (v1)

*   Multi-user management, authentication, or cloud account tiers[cite: 1].
*   Automatic job application submission or browser bot auto-apply workflows.
*   Cover letter generation (reserved for v2).
*   Multi-language resume translation (English only for v1).
*   Arbitrary free-form visual PDF layout editing (all outputs follow structured, ATS-standard templates).

---

## Output Quality & Anti-Hallucination Standards

*   **Zero-Hallucination Tolerance:** The system must never invent employers, degree titles, dates, certifications, tools, or numeric performance metrics.
*   **Grounding Enforcement:** Every metric or achievement claim must have direct provenance in the source resume. If a metric does not exist, the rewriter may rephrase for clarity and scope but must not inject arbitrary statistics.
*   **ATS Readability:** Rendered PDFs must maintain single-column or ATS-tested layouts with standard section headings and machine-readable text layers.

---

## Phases and Success Criteria

Build in these phases, in order. Do not start a phase until every success criterion of the previous phase is demonstrably met[cite: 1].

### Phase 1 — Ingestion, Extraction & Schemas

**Goals**
Establish the data ingestion layer to reliably parse PDF resumes, scrape job URLs, parse job PDFs, and validate the extracted text into typed Pydantic models.

**Success Criteria**
1. Given a multi-page resume PDF, the parser outputs structured JSON containing distinct sections (contact, experience, education, skills, projects) with no missing text blocks.
2. Given a target job PDF or a dynamic web URL (e.g., Greenhouse, Lever, Workday), the ingestion module extracts the complete job posting body without site navigation boilerplate.
3. Ingestion failures (corrupt PDFs, invalid URLs, HTTP 403s) raise typed errors with clear diagnostic messages.

**Unit & Integration Tests**
*   `test_pdf_resume_extraction_completeness`: Verifies all text blocks from sample benchmark resumes are present in the parsed output.
*   `test_job_url_scraper_spa_support`: Verifies that dynamic JavaScript-rendered job pages return raw posting text.
*   `test_schema_validation_success_and_failure`: Asserts valid extraction payloads pass Pydantic validation while incomplete schemas throw expected validation errors.

---

### Phase 2 — Profiler Agents & Evaluator Gap Analysis

**Goals**
Build the Job Profiler, Resume Profiler, and the Recruiter/Evaluator Agent to produce structured role requirements, candidate representations, and an objective gap analysis report.

**Success Criteria**
1. The Job Profiler extracts core requirements, bonus qualifications, and required tech stacks into structured lists.
2. The Resume Profiler extracts individual work experiences, isolating each bullet point with its underlying action verbs, technical tools, and metrics.
3. The Recruiter/Evaluator Agent outputs a structured Delta Report detailing matched skills, missing keywords, fit score, and line-by-line optimization directives.

**Unit & Integration Tests**
*   `test_job_profiler_entity_extraction`: Asserts specific required qualifications in a test job description are captured in the schema.
*   `test_resume_profiler_bullet_decomposition`: Verifies individual bullet points and their associated metadata are correctly parsed.
*   `test_recruiter_agent_gap_identification`: Asserts that known discrepancies between a sample resume and job description are correctly flagged in the generated Delta Report.

---

### Phase 3 — Tailoring Agent & Anti-Hallucination Guardrails

**Goals**
Implement the Copywriter/Tailoring Agent to rephrase resume sections and the Verification/Critic Agent to audit claims against source history.

**Success Criteria**
1. The Tailoring Agent rewrites bullet points to align with job keywords and XYZ impact formatting while preserving the candidate's original intent.
2. The Verification Agent accurately scores each tailored line for factual entailment against the source resume.
3. Any rewritten line introducing non-existent tools, inflated job titles, or fabricated metrics is rejected and sent back for regeneration.

**Unit & Integration Tests**
*   `test_tailoring_agent_keyword_alignment`: Verifies that targeted keywords from the gap analysis appear naturally in rewritten bullet points.
*   `test_verification_agent_detects_hallucinations`: Asserts that synthetic test cases with injected fake statistics or tools trigger a rejection flag.
*   `test_verification_agent_passes_faithful_paraphrase`: Verifies that faithful rephrasing passes entailment checks without false positives.

---

### Phase 4 — Document Generation & ATS Typesetting

**Goals**
Convert the verified structured resume data into a production-ready, ATS-compliant PDF using a deterministic typesetting engine (Typst, LaTeX, or WeasyPrint).

**Success Criteria**
1. The document engine generates a visually balanced, single-page or two-page PDF without overflow artifacts or broken layouts.
2. The output PDF contains selectable, ATS-readable text layers matching standard resume section hierarchies.
3. A JSON diff is generated showing line-by-line comparisons between original and tailored content.

**Unit & Integration Tests**
*   `test_pdf_compilation_success`: Asserts that valid tailored JSON compiles to a PDF file without engine errors.
*   `test_pdf_text_extractability`: Extracts text from the compiled PDF to ensure all tailored sections remain machine-readable and accurately ordered.
*   `test_diff_generator_accuracy`: Asserts that changed, added, or unchanged bullet points are properly categorized in the diff output.

---

### Phase 5 — Full Orchestration & Interface

**Goals**
Connect all components into an end-to-end executable pipeline with an interactive user interface (CLI or Web UI) for uploading inputs, viewing diffs, and downloading the final PDF.

**Success Criteria**
1. Users can run the application with a single command, provide a resume PDF and job posting (PDF or URL), and receive a verified tailored PDF[cite: 1].
2. The user interface displays the intermediate recruiter evaluation, side-by-side bullet comparisons, and verification pass/fail status.
3. Users can accept, reject, or manually adjust individual tailored suggestions before final PDF compilation.

**Unit & Integration Tests**
*   `test_end_to_end_pipeline_execution`: Runs the full pipeline from raw inputs to final compiled PDF and verifies exit status and output integrity.
*   `test_cli_or_api_route_handling`: Asserts that file upload endpoints or CLI arguments correctly trigger the orchestrator workflow.

---

## Final Success Criteria

The project is complete, and the Coding Agent may stop, when **all** of the following are true:

- A non-technical person can start the app with a single documented command and open it in a browser[cite: 1].
- The pipeline accepts both PDF and URL-based job descriptions, parsing both formats reliably.
- The recruiter evaluation provides actionable, structured gap analysis.
- All rewritten bullet points strictly pass anti-hallucination verification against the source resume.
- The compiled output PDF is clean, professionally typeset, and fully ATS-parseable.
- All unit and integration test suites across Phases 1 through 5 pass deterministically[cite: 1].
- The complete workflow has been validated end-to-end on multiple real-world resume and job posting combinations, confirming factual accuracy, visual layout quality, and keyword alignment.