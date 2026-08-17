"""Typed errors raised by the ingestion layer."""

from __future__ import annotations


class IngestionError(Exception):
    """Base class for all ingestion-layer failures."""


class CorruptPDFError(IngestionError):
    """Raised when a PDF cannot be opened or contains no extractable text."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Corrupt or unreadable PDF at '{path}': {reason}")


class InvalidURLError(IngestionError):
    """Raised when a job posting URL is malformed or unreachable."""

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"Invalid URL '{url}': {reason}")


class HTTPFetchError(IngestionError):
    """Raised when fetching a job posting URL returns a failing HTTP status."""

    def __init__(self, url: str, status_code: int) -> None:
        self.url = url
        self.status_code = status_code
        super().__init__(f"HTTP {status_code} while fetching '{url}'")


class InsufficientContentError(IngestionError):
    """Raised when scraped/parsed content is empty or too short to be a real posting."""

    def __init__(self, source: str, char_count: int) -> None:
        self.source = source
        self.char_count = char_count
        super().__init__(
            f"Extracted content from '{source}' was only {char_count} characters "
            "and is likely navigation boilerplate or an unrendered SPA shell"
        )
