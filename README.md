# Resume Tailor AI

Multi-agent system that takes a resume (PDF) and a target job (PDF or URL) and produces
a customized, ATS-friendly resume PDF — with a strict anti-hallucination guardrail so
rewritten bullets never introduce facts, tools, or metrics that aren't in the source resume.

Built as a LangGraph pipeline: Job Profiler + Resume Profiler → Recruiter/Evaluator →
Tailoring Agent ⇄ Verification Agent (retry loop) → Typst PDF compiler.

## Setup

1. **Install dependencies** (Python 3.11+):

   ```sh
   python3 -m venv .venv
   .venv/bin/pip install -e ".[dev]"
   .venv/bin/playwright install chromium   # needed for JS-rendered job postings
   ```

2. **Add your DeepSeek API key.** Get one at [platform.deepseek.com](https://platform.deepseek.com):

   ```sh
   cp .env.example .env
   # then edit .env and set DEEPSEEK_API_KEY=sk-...
   ```

## Run the app (single command)

```sh
.venv/bin/streamlit run app.py
```

This opens the web UI at `http://localhost:8501` in your browser. From there:

1. Upload your resume PDF and the target job (a URL or a PDF upload).
2. Click **Analyze fit** to see the recruiter evaluation — fit score, matched
   qualifications, missing keywords, and specific recommendations.
3. Click **Tailor bullets** to rewrite your resume bullets against the job, with each
   one automatically checked for hallucinated tools/metrics/claims against your original
   resume (failed bullets are retried automatically).
4. Review each bullet side-by-side (original vs. tailored, with a pass/fail verification
   badge) and choose **Tailored**, **Original**, or **Edit** for each one.
5. Click **Compile final PDF** and download the result.

## CLI (non-interactive / scripting)

```sh
.venv/bin/resume-tailor --resume resume.pdf --job-url "https://example.com/jobs/123"
.venv/bin/resume-tailor --resume resume.pdf --job-pdf job.pdf --output tailored.pdf
```

Runs the full pipeline end-to-end (no manual review step) and writes the tailored,
verified PDF straight to `--output` (default: `tailored_resume.pdf`).

## Running tests

```sh
.venv/bin/pytest              # hermetic suite — no API key needed, runs in seconds
```

A handful of tests are gated behind a live `DEEPSEEK_API_KEY` (real entity-extraction and
anti-hallucination accuracy checks) and are skipped automatically without one.

## Project layout

```
src/resume_tailor/
  ingestion/     Phase 1 — PDF/URL parsing into typed Pydantic schemas
  agents/        Phase 2-3 — Job/Resume Profiler, Recruiter/Evaluator, Tailoring, Verification
  graph/         LangGraph StateGraph wiring the agents together, with a verification retry loop
  document/      Phase 4 — Typst PDF typesetting, diff generation
  schemas/       Pydantic models shared across every phase
  orchestrator.py  Phase 5 — single run_pipeline() entry point
  cli.py         Command-line entry point
  webapp.py      Streamlit web UI
app.py           `streamlit run app.py` entry point
```
