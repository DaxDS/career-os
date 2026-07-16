"""Canadian-format resume JSON models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResumeExperience(BaseModel):
    title: str
    employer: str = ""
    dates: str = ""
    location: str = ""
    bullets: list[str] = Field(default_factory=list)


class ResumeEducation(BaseModel):
    institution: str = ""
    degree: str = ""
    dates: str = ""


class ResumeDocument(BaseModel):
    full_name: str = ""
    contact: dict[str, str] = Field(default_factory=dict)
    summary: str = ""
    experience: list[ResumeExperience] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class TailoredResume(ResumeDocument):
    changes_made: list[dict[str, str]] = Field(default_factory=list)


class CoverLetter(BaseModel):
    full_text: str
    word_count: int = 0
