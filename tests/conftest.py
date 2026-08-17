"""Shared pytest fixtures: fixture-generating PDFs and a local HTML test server.

Tests run against localhost rather than the real internet so they're
hermetic and don't depend on external site availability.
"""

from __future__ import annotations

import http.server
import threading
from pathlib import Path

import pytest

from tests.fixtures import generate_pdfs

FIXTURES_DIR = Path(__file__).parent / "fixtures"
HTML_DIR = FIXTURES_DIR / "html"


class _Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HTML_DIR), **kwargs)

    def do_GET(self) -> None:  # noqa: N802 (stdlib method name)
        if self.path.startswith("/forbidden"):
            self.send_response(403)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return
        super().do_GET()

    def log_message(self, format: str, *args) -> None:  # silence per-request logging
        pass


@pytest.fixture(scope="session")
def html_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.fixture(scope="session")
def resume_pdf_path(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("pdfs") / "sample_resume.pdf"
    generate_pdfs.build_resume_pdf(str(path))
    return str(path)


@pytest.fixture(scope="session")
def job_pdf_path(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("pdfs") / "sample_job.pdf"
    generate_pdfs.build_job_pdf(str(path))
    return str(path)


@pytest.fixture(scope="session")
def corrupt_pdf_path(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("pdfs") / "corrupt.pdf"
    generate_pdfs.build_corrupt_pdf(str(path))
    return str(path)
