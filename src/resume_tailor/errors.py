"""Typed errors raised across the pipeline."""

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


class MissingResumeSectionError(IngestionError):
    """Raised when a resume PDF's section headings couldn't all be detected."""

    def __init__(self, path: str, found: list[str], missing: list[str]) -> None:
        self.path = path
        self.found = found
        self.missing = missing
        found_str = ", ".join(found) if found else "none"
        missing_str = ", ".join(missing)
        super().__init__(
            f"Could not detect a '{missing_str}' section heading in '{path}'. "
            f"Sections detected: {found_str}. "
            "This usually means the resume uses an unusual heading (e.g. 'Career History' "
            "instead of 'Experience') or a multi-column layout that confuses reading order. "
            "Try renaming the heading to a standard one (Experience, Education, Skills) or "
            "using a single-column layout."
        )


class LLMResponseError(Exception):
    """Raised when the model's structured-output response couldn't be parsed
    as valid, schema-conforming JSON after retries.

    DeepSeek's JSON mode has no server-side schema enforcement (unlike some
    other providers), and their own API docs note it can occasionally return
    an empty response — this is the terminal error after retrying that.
    """

    def __init__(self, model: str, reason: str) -> None:
        self.model = model
        self.reason = reason
        super().__init__(f"Model '{model}' did not return a usable response: {reason}")


class DocumentCompilationError(Exception):
    """Raised when the Typst engine fails to compile a resume to PDF."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Resume PDF compilation failed: {reason}")
