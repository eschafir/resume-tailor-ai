"""Job posting URL ingestion: fast static-HTML extraction with a headless
browser fallback for JavaScript-rendered SPAs (Greenhouse, Lever, Workday, etc.)."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
import trafilatura
from playwright.sync_api import sync_playwright

from resume_tailor.errors import HTTPFetchError, InsufficientContentError, InvalidURLError
from resume_tailor.schemas.job import ExtractionMethod, JobSourceType, MIN_POSTING_LENGTH, RawJobPosting

_USER_AGENT = (
    "Mozilla/5.0 (compatible; ResumeTailorAI/0.1; +https://example.invalid/bot)"
)
_HTTP_TIMEOUT_SECONDS = 15.0
_RENDER_TIMEOUT_MS = 20_000


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise InvalidURLError(url, "must be an absolute http(s) URL")


def _fetch_static_html(url: str) -> str:
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": _USER_AGENT},
            timeout=_HTTP_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
    except httpx.RequestError as exc:
        raise InvalidURLError(url, f"could not connect: {exc}") from exc

    if response.status_code >= 400:
        raise HTTPFetchError(url, response.status_code)
    return response.text


def _fetch_rendered_html(url: str) -> str:
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                page = browser.new_page(user_agent=_USER_AGENT)
                page.goto(url, wait_until="networkidle", timeout=_RENDER_TIMEOUT_MS)
                return page.content()
            finally:
                browser.close()
    except Exception as exc:  # playwright raises its own TimeoutError/Error types
        raise InvalidURLError(url, f"headless render failed: {exc}") from exc


def _extract_body_text(html: str) -> str:
    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
    )
    return (extracted or "").strip()


def _extract_title(html: str) -> str | None:
    metadata = trafilatura.extract_metadata(html)
    return metadata.title if metadata and metadata.title else None


def scrape_job_url(url: str, *, min_length: int = MIN_POSTING_LENGTH) -> RawJobPosting:
    """Fetch and extract a job posting's full body text from a URL.

    Tries a fast static fetch first; if the extracted content is too short
    (typical of a JS-rendered SPA shell), falls back to headless rendering.
    """
    _validate_url(url)

    static_html = _fetch_static_html(url)
    static_text = _extract_body_text(static_html)

    if len(static_text) >= min_length:
        return RawJobPosting(
            source_type=JobSourceType.URL,
            source=url,
            raw_text=static_text,
            title=_extract_title(static_html),
            extraction_method=ExtractionMethod.STATIC_HTML,
            fetched_at=datetime.now(timezone.utc),
        )

    rendered_html = _fetch_rendered_html(url)
    rendered_text = _extract_body_text(rendered_html)

    if len(rendered_text) < min_length:
        raise InsufficientContentError(url, len(rendered_text))

    return RawJobPosting(
        source_type=JobSourceType.URL,
        source=url,
        raw_text=rendered_text,
        title=_extract_title(rendered_html),
        extraction_method=ExtractionMethod.RENDERED_SPA,
        fetched_at=datetime.now(timezone.utc),
    )
