from __future__ import annotations

import pytest

from resume_tailor.errors import HTTPFetchError, InvalidURLError
from resume_tailor.ingestion.web_scraper import scrape_job_url
from resume_tailor.schemas.job import ExtractionMethod


def test_job_url_scraper_spa_support(html_server):
    posting = scrape_job_url(f"{html_server}/spa_job.html")

    assert posting.extraction_method == ExtractionMethod.RENDERED_SPA
    assert "Staff Machine Learning Engineer" in posting.raw_text
    assert "Fjord Analytics" in posting.raw_text
    assert "feature stores" in posting.raw_text
    # The unrendered shell text must not leak through as the final result.
    assert posting.raw_text.strip() != "Loading..."


def test_job_url_scraper_static_page_strips_boilerplate(html_server):
    posting = scrape_job_url(f"{html_server}/static_job.html")

    assert posting.extraction_method == ExtractionMethod.STATIC_HTML
    assert "Senior Backend Engineer" in posting.raw_text
    assert "Northwind Technologies" in posting.raw_text
    assert "distributed systems fundamentals" in posting.raw_text
    # Navigation/footer boilerplate should be excluded from the extracted body.
    assert "Sign In" not in posting.raw_text
    assert "Privacy Policy" not in posting.raw_text
    assert "cookies to improve your experience" not in posting.raw_text


def test_job_url_scraper_http_403_raises_typed_error(html_server):
    with pytest.raises(HTTPFetchError) as exc_info:
        scrape_job_url(f"{html_server}/forbidden")
    assert exc_info.value.status_code == 403


def test_job_url_scraper_invalid_url_raises_typed_error():
    with pytest.raises(InvalidURLError):
        scrape_job_url("not-a-valid-url")


def test_job_url_scraper_unreachable_host_raises_typed_error():
    with pytest.raises(InvalidURLError):
        scrape_job_url("http://127.0.0.1:1/unreachable")
