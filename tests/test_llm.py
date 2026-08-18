"""Tests for the DeepSeek structured-output retry logic (agents/llm.py).

DeepSeek's JSON mode has no server-side schema enforcement and their own
docs note it can occasionally return an empty response — these tests pin
down the retry-then-raise-a-typed-error behavior added to handle that.
"""

from __future__ import annotations

import pytest

from resume_tailor.agents.llm import parse_structured
from resume_tailor.errors import LLMResponseError
from resume_tailor.schemas.job_profile import JobProfile
from tests.fakes import FlakySequenceDeepSeekClient


@pytest.fixture(autouse=True)
def _no_retry_delay(monkeypatch):
    import resume_tailor.agents.llm as llm_module

    monkeypatch.setattr(llm_module.time, "sleep", lambda _seconds: None)


def test_parse_structured_retries_on_empty_response():
    expected = JobProfile(title="Engineer", role_summary="...")
    client = FlakySequenceDeepSeekClient(["", "", expected.model_dump_json()])

    result = parse_structured(
        client, model="deepseek-v4-pro", system="sys", user_content="job text", schema=JobProfile
    )

    assert result == expected
    assert len(client.calls) == 3


def test_parse_structured_retries_on_invalid_json():
    expected = JobProfile(title="Engineer", role_summary="...")
    client = FlakySequenceDeepSeekClient(["not valid json{{{", expected.model_dump_json()])

    result = parse_structured(
        client, model="deepseek-v4-pro", system="sys", user_content="job text", schema=JobProfile
    )

    assert result == expected
    assert len(client.calls) == 2
    # The retry attempt reinforces the JSON-only instruction.
    assert "IMPORTANT" in client.calls[1]["messages"][0]["content"]


def test_parse_structured_retries_on_schema_mismatch():
    expected = JobProfile(title="Engineer", role_summary="...")
    # Valid JSON, but missing the required "title" field.
    client = FlakySequenceDeepSeekClient(['{"role_summary": "..."}', expected.model_dump_json()])

    result = parse_structured(
        client, model="deepseek-v4-pro", system="sys", user_content="job text", schema=JobProfile
    )

    assert result == expected
    assert len(client.calls) == 2


def test_parse_structured_raises_typed_error_after_max_attempts():
    client = FlakySequenceDeepSeekClient(["", "", ""])

    with pytest.raises(LLMResponseError):
        parse_structured(
            client, model="deepseek-v4-pro", system="sys", user_content="job text", schema=JobProfile
        )

    assert len(client.calls) == 3
