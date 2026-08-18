"""A minimal stand-in for the OpenAI-compatible `chat.completions.create` surface.

Lets agent unit tests exercise prompt construction and schema validation
deterministically, without a live DeepSeek API call.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel


class _FakeCompletions:
    def __init__(self, json_content: str) -> None:
        self._json_content = json_content
        self.calls: list[dict] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        message = SimpleNamespace(content=self._json_content)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


class _FakeChat:
    def __init__(self, json_content: str) -> None:
        self.completions = _FakeCompletions(json_content)


class FakeDeepSeekClient:
    """Returns a pre-built parsed model (serialized to JSON) for every call."""

    def __init__(self, parsed_output: BaseModel) -> None:
        self.chat = _FakeChat(parsed_output.model_dump_json())
        self._completions = self.chat.completions

    @property
    def calls(self) -> list[dict]:
        return self._completions.calls


class _FakeSequentialCompletions:
    def __init__(self, raw_responses: list[str]) -> None:
        self._raw_responses = raw_responses
        self.calls: list[dict] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        raw = self._raw_responses[len(self.calls)]
        self.calls.append(kwargs)
        message = SimpleNamespace(content=raw)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


class FlakySequenceDeepSeekClient:
    """Returns a different raw response body on each successive call.

    Simulates DeepSeek's documented "may occasionally return empty content"
    behavior, and malformed JSON — for testing the retry logic in
    `parse_structured`. `raw_responses` is consumed in order, one per call;
    calling more times than there are entries raises IndexError (a test bug,
    not a code-under-test bug).
    """

    def __init__(self, raw_responses: list[str]) -> None:
        self.chat = SimpleNamespace(completions=_FakeSequentialCompletions(raw_responses))

    @property
    def calls(self) -> list[dict]:
        return self.chat.completions.calls
