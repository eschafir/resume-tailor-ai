"""Compiles a RenderableResume into an ATS-friendly PDF via Typst.

Typst is used over LaTeX/WeasyPrint because its `typst` PyPI package ships a
self-contained compiled binary — no system-level LaTeX distribution or
Pango/Cairo install required — while still producing a real, selectable text
layer (not a rasterized image), which is what ATS parsers need.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import typst

from resume_tailor.errors import DocumentCompilationError
from resume_tailor.schemas.render import RenderableResume

_TEMPLATE_PATH = Path(__file__).parent / "templates" / "resume.typ"


def compile_resume_pdf(resume: RenderableResume, output_path: str) -> None:
    """Render `resume` to a PDF at `output_path`."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        template_copy = tmp / "resume.typ"
        shutil.copy(_TEMPLATE_PATH, template_copy)
        (tmp / "resume_data.json").write_text(resume.model_dump_json())
        compiled_path = tmp / "resume.pdf"

        try:
            typst.compile(str(template_copy), output=str(compiled_path), root=str(tmp))
        except Exception as exc:
            raise DocumentCompilationError(str(exc)) from exc

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(compiled_path), output_path)
