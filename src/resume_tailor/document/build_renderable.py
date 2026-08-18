"""Maps the verified CandidateProfile + TailoredResume onto the flat
RenderableResume the Typst template consumes.

Every original bullet resolves to its tailored counterpart when one exists;
otherwise the original text carries through unchanged (e.g. a bullet the
Verification Agent never cleared within the retry budget).
"""

from __future__ import annotations

from resume_tailor.schemas.candidate import BulletPoint, CandidateProfile
from resume_tailor.schemas.render import (
    RenderableEducation,
    RenderableExperience,
    RenderableProject,
    RenderableResume,
)
from resume_tailor.schemas.tailoring import TailoredResume


def build_renderable_resume(
    candidate: CandidateProfile,
    tailored: TailoredResume,
) -> RenderableResume:
    tailored_by_original = {b.original_text: b.tailored_text for b in tailored.tailored_bullets}

    def resolve(bullet: BulletPoint) -> str:
        return tailored_by_original.get(bullet.text, bullet.text)

    experience = [
        RenderableExperience(
            company=entry.company,
            title=entry.title,
            start_date=entry.start_date,
            end_date=entry.end_date,
            bullets=[resolve(b) for b in entry.bullets],
        )
        for entry in candidate.experience
    ]
    education = [
        RenderableEducation(
            institution=entry.institution,
            degree=entry.degree,
            field_of_study=entry.field_of_study,
            graduation_date=entry.graduation_date,
        )
        for entry in candidate.education
    ]
    projects = [
        RenderableProject(name=entry.name, bullets=[resolve(b) for b in entry.bullets])
        for entry in candidate.projects
    ]

    return RenderableResume(
        full_name=candidate.full_name or "",
        contact_summary=candidate.contact_summary,
        summary=tailored.tailored_summary,
        experience=experience,
        education=education,
        hard_skills=candidate.hard_skills,
        soft_skills=candidate.soft_skills,
        projects=projects,
    )
