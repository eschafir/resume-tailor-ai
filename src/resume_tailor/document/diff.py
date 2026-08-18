"""Generates the line-by-line diff between the original and tailored resume (Phase 4)."""

from __future__ import annotations

from resume_tailor.schemas.candidate import CandidateProfile
from resume_tailor.schemas.diff import BulletDiff, DiffStatus, ResumeDiff
from resume_tailor.schemas.tailoring import TailoredResume


def generate_diff(candidate: CandidateProfile, tailored: TailoredResume) -> ResumeDiff:
    original_texts = {b.text for entry in candidate.experience for b in entry.bullets}
    original_texts |= {b.text for entry in candidate.projects for b in entry.bullets}

    diffs: list[BulletDiff] = []
    matched_originals: set[str] = set()

    for tb in tailored.tailored_bullets:
        if tb.original_text in original_texts:
            matched_originals.add(tb.original_text)
            status = (
                DiffStatus.UNCHANGED
                if tb.tailored_text.strip() == tb.original_text.strip()
                else DiffStatus.CHANGED
            )
            original_text = tb.original_text
        else:
            status = DiffStatus.ADDED
            original_text = None
        diffs.append(
            BulletDiff(
                company=tb.company,
                original_text=original_text,
                tailored_text=tb.tailored_text,
                status=status,
            )
        )

    # Original bullets the Tailoring Agent never touched carry through verbatim.
    for entry in candidate.experience:
        for bullet in entry.bullets:
            if bullet.text not in matched_originals:
                diffs.append(
                    BulletDiff(
                        company=entry.company,
                        original_text=bullet.text,
                        tailored_text=bullet.text,
                        status=DiffStatus.UNCHANGED,
                    )
                )
    for entry in candidate.projects:
        for bullet in entry.bullets:
            if bullet.text not in matched_originals:
                diffs.append(
                    BulletDiff(
                        company=entry.name,
                        original_text=bullet.text,
                        tailored_text=bullet.text,
                        status=DiffStatus.UNCHANGED,
                    )
                )

    return ResumeDiff(bullets=diffs)
