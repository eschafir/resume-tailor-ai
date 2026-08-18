"""Shared DeepSeek API client and structured-output helper for all agents.

DeepSeek's Chat Completions API is OpenAI-compatible but only supports
generic JSON mode (`response_format={"type": "json_object"}`) — it has no
schema-constrained structured-output guarantee. To still get typed, validated
Pydantic output, the target schema is embedded in the system prompt and the
raw JSON response is validated against it after the fact.

DeepSeek's own docs note their API "may occasionally return empty content"
in JSON mode — this is retried automatically rather than surfaced as a raw
JSONDecodeError.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from resume_tailor.errors import LLMResponseError

load_dotenv()

DEFAULT_MODEL = os.environ.get("RESUME_TAILOR_MODEL", "deepseek-v4-pro")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

T = TypeVar("T", bound=BaseModel)

_MAX_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 1.5


def get_client() -> OpenAI:
    return OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url=DEEPSEEK_BASE_URL)


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        if stripped.endswith("```"):
            stripped = stripped.rsplit("```", 1)[0]
    return stripped.strip()


def parse_structured(
    client: Any,
    *,
    model: str,
    system: str,
    user_content: str,
    schema: type[T],
    max_tokens: int = 8192,
) -> T:
    """Call the model and validate its JSON response against `schema`.

    Retries on an empty response, invalid JSON, or a schema mismatch — all
    observed DeepSeek JSON-mode failure modes — before raising LLMResponseError.
    """
    schema_json = json.dumps(schema.model_json_schema())
    base_system = (
        f"{system}\n\n"
        "Respond with a single JSON object that strictly matches this JSON Schema "
        f"and nothing else — no prose, no markdown code fences:\n{schema_json}"
    )

    last_error: LLMResponseError | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        system_for_attempt = base_system
        if attempt > 1:
            system_for_attempt += (
                "\n\nIMPORTANT: your previous response was empty or was not valid JSON "
                "matching the schema. Respond with ONLY the JSON object — no empty "
                "response, no prose, no markdown code fences."
            )

        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_for_attempt},
                {"role": "user", "content": user_content},
            ],
        )
        raw = response.choices[0].message.content

        if not raw or not raw.strip():
            last_error = LLMResponseError(model, "the model returned an empty response")
        else:
            try:
                data = json.loads(_strip_code_fence(raw))
                return schema.model_validate(data)
            except json.JSONDecodeError as exc:
                last_error = LLMResponseError(model, f"response was not valid JSON ({exc})")
            except ValidationError as exc:
                last_error = LLMResponseError(model, f"response didn't match the expected schema ({exc})")

        if attempt < _MAX_ATTEMPTS:
            time.sleep(_RETRY_DELAY_SECONDS)

    assert last_error is not None
    raise last_error
