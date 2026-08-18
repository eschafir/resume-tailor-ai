"""Schema for the original-vs-tailored resume diff (Phase 4)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class DiffStatus(str, Enum):
    UNCHANGED = "unchanged"
    CHANGED = "changed"
    ADDED = "added"


class BulletDiff(BaseModel):
    company: str
    original_text: str | None
    tailored_text: str
    status: DiffStatus


class ResumeDiff(BaseModel):
    bullets: list[BulletDiff]
