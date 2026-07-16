"""Jinja2 HTML render + Playwright PDF."""

from __future__ import annotations

import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from lib.resume_schema import ResumeDocument

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_resume_html(resume: ResumeDocument | dict) -> str:
    data = resume.model_dump() if isinstance(resume, ResumeDocument) else resume
    template = _env.get_template("resume_canadian.html")
    return template.render(**data)


def html_to_pdf(html: str, output_path: Path) -> bool:
    """Render ATS-safe PDF via Playwright. Returns False if Playwright unavailable."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(html)
        tmp_path = tmp.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file:///{tmp_path.replace(chr(92), '/')}")
            page.pdf(
                path=str(output_path),
                format="Letter",
                print_background=False,
                margin={"top": "0.4in", "bottom": "0.4in", "left": "0.5in", "right": "0.5in"},
            )
            browser.close()
        return True
    except Exception:
        return False
    finally:
        Path(tmp_path).unlink(missing_ok=True)
