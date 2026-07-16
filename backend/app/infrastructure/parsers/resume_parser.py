import re
from pathlib import Path

from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)

SECTION_PATTERNS = [
    (r"^(experience|work experience|employment)", "experience"),
    (r"^(education|academic)", "education"),
    (r"^(skills|technical skills|core competencies)", "skills"),
    (r"^(certifications?|licenses?)", "certifications"),
    (r"^(summary|profile|objective|about)", "summary"),
    (r"^(projects?)", "projects"),
]


class ResumeParser:
    """Parse PDF, DOCX, and plain-text resumes into structured JSON."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}

    def parse_file(self, file_path: Path) -> dict:
        suffix = file_path.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {suffix}")

        if suffix == ".pdf":
            text = self._parse_pdf(file_path)
        elif suffix in (".docx", ".doc"):
            text = self._parse_docx(file_path)
        else:
            text = file_path.read_text(encoding="utf-8", errors="replace")

        return self._structure_text(text)

    def _parse_pdf(self, file_path: Path) -> str:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def _parse_docx(self, file_path: Path) -> str:
        from docx import Document

        doc = Document(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    def _structure_text(self, text: str) -> dict:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        sections: dict[str, list[str]] = {"header": []}
        current_section = "header"

        for line in lines:
            lower = line.lower()
            matched = False
            for pattern, section_name in SECTION_PATTERNS:
                if re.match(pattern, lower):
                    current_section = section_name
                    sections[current_section] = []
                    matched = True
                    break
            if not matched:
                sections.setdefault(current_section, []).append(line)

        return {
            "raw_text": text,
            "summary": " ".join(sections.get("summary", [])),
            "header": sections.get("header", [])[:5],
            "experience": self._parse_experience(sections.get("experience", [])),
            "skills": self._parse_skills(sections.get("skills", [])),
            "education": self._parse_education(sections.get("education", [])),
            "certifications": sections.get("certifications", []),
            "projects": sections.get("projects", []),
        }

    def _parse_experience(self, lines: list[str]) -> list[dict]:
        entries: list[dict] = []
        current: dict | None = None
        date_pattern = re.compile(
            r"(\w+\s+\d{4})\s*[-–—]\s*(\w+\s+\d{4}|present|current)", re.IGNORECASE
        )

        for line in lines:
            is_bullet = line.startswith(("-", "•", "*", "·"))
            if is_bullet and current:
                current["bullets"].append(line.lstrip("-•*· ").strip())
            elif date_pattern.search(line):
                if current:
                    entries.append(current)
                current = {
                    "employer": line,
                    "title": "",
                    "dates": date_pattern.search(line).group(0),
                    "location": "",
                    "bullets": [],
                }
            elif current and not current.get("title"):
                current["title"] = line
            elif not current:
                current = {"employer": line, "title": "", "dates": "", "location": "", "bullets": []}

        if current:
            entries.append(current)
        return entries

    def _parse_skills(self, lines: list[str]) -> list[str]:
        skills: list[str] = []
        for line in lines:
            parts = re.split(r"[,;|•·]", line)
            skills.extend(p.strip() for p in parts if p.strip())
        return skills

    def _parse_education(self, lines: list[str]) -> list[dict]:
        return [{"institution": line, "degree": "", "dates": ""} for line in lines]
