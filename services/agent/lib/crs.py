"""Comprehensive Ranking System (CRS) scoring engine.

Implements the official Express Entry CRS grid. Point tables are transcribed from
IRCC's published criteria and versioned here so a change to the grid is a reviewable
diff rather than a silent behaviour change.

Grid version: 2026-08-03.

Two facts drive the whole model and are easy to get wrong:

1.  **Arranged employment is worth 0 points.** IRCC removed arranged-employment CRS
    points on 2025-03-25 and they remain removed. A job offer never raises a CRS
    score. A job only moves PR odds indirectly — by accruing Canadian experience,
    by making a candidate eligible for a category-based round, or by unlocking a
    provincial nomination (600 points).

2.  Every factor is capped, and the caps differ depending on whether the candidate
    has an accompanying spouse or common-law partner.

Maximum total: 1200 (600 core + spouse + transferability, 600 additional).

Informational only. Not immigration advice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

GRID_VERSION = "2026-08-03"

MAX_TOTAL = 1200
MAX_CORE_WITH_SPOUSE = 460
MAX_CORE_WITHOUT_SPOUSE = 500
MAX_SPOUSE_FACTORS = 40
MAX_TRANSFERABILITY = 100
MAX_ADDITIONAL = 600

EducationLevel = Literal[
    "none",
    "secondary",
    "one_year_post_secondary",
    "two_year_post_secondary",
    "bachelors_or_three_year",
    "two_or_more_credentials",
    "masters_or_professional",
    "doctoral",
]

#: Ordering used for "at least a X credential" comparisons.
EDUCATION_ORDER: list[str] = [
    "none",
    "secondary",
    "one_year_post_secondary",
    "two_year_post_secondary",
    "bachelors_or_three_year",
    "two_or_more_credentials",
    "masters_or_professional",
    "doctoral",
]

# --- Core / human capital -------------------------------------------------

# age -> (without_spouse, with_spouse)
_AGE_POINTS: dict[int, tuple[int, int]] = {
    17: (0, 0),
    18: (99, 90),
    19: (105, 95),
    20: (110, 100),
    21: (110, 100),
    22: (110, 100),
    23: (110, 100),
    24: (110, 100),
    25: (110, 100),
    26: (110, 100),
    27: (110, 100),
    28: (110, 100),
    29: (110, 100),
    30: (105, 95),
    31: (99, 90),
    32: (94, 85),
    33: (88, 80),
    34: (83, 75),
    35: (77, 70),
    36: (72, 65),
    37: (66, 60),
    38: (61, 55),
    39: (55, 50),
    40: (50, 45),
    41: (39, 35),
    42: (28, 25),
    43: (17, 15),
    44: (6, 5),
}

_EDUCATION_POINTS: dict[str, tuple[int, int]] = {
    "none": (0, 0),
    "secondary": (30, 28),
    "one_year_post_secondary": (90, 84),
    "two_year_post_secondary": (98, 91),
    "bachelors_or_three_year": (120, 112),
    "two_or_more_credentials": (128, 119),
    "masters_or_professional": (135, 126),
    "doctoral": (150, 140),
}

# First official language, points PER ABILITY (reading/writing/listening/speaking).
def _first_language_points(clb: int, has_spouse: bool) -> int:
    if clb >= 10:
        return 32 if has_spouse else 34
    if clb == 9:
        return 29 if has_spouse else 31
    if clb == 8:
        return 22 if has_spouse else 23
    if clb == 7:
        return 16 if has_spouse else 17
    if clb == 6:
        return 8 if has_spouse else 9
    if clb in (4, 5):
        return 6
    return 0


def _second_language_points(clb: int) -> int:
    """Second official language, per ability. Overall cap applied by caller."""
    if clb >= 9:
        return 6
    if clb in (7, 8):
        return 3
    if clb in (5, 6):
        return 1
    return 0


# years of Canadian work experience -> (without_spouse, with_spouse)
_CANADIAN_EXPERIENCE_POINTS: dict[int, tuple[int, int]] = {
    0: (0, 0),
    1: (40, 35),
    2: (53, 46),
    3: (64, 56),
    4: (72, 63),
    5: (80, 70),
}

# --- Spouse factors -------------------------------------------------------

_SPOUSE_EDUCATION_POINTS: dict[str, int] = {
    "none": 0,
    "secondary": 2,
    "one_year_post_secondary": 6,
    "two_year_post_secondary": 7,
    "bachelors_or_three_year": 8,
    "two_or_more_credentials": 9,
    "masters_or_professional": 10,
    "doctoral": 10,
}

_SPOUSE_CANADIAN_EXPERIENCE_POINTS: dict[int, int] = {0: 0, 1: 5, 2: 7, 3: 8, 4: 9, 5: 10}


def _spouse_language_points(clb: int) -> int:
    if clb >= 9:
        return 5
    if clb in (7, 8):
        return 3
    if clb in (5, 6):
        return 1
    return 0


@dataclass
class LanguageScores:
    """CLB level per ability. NCLC for French uses the same numeric scale."""

    reading: int = 0
    writing: int = 0
    listening: int = 0
    speaking: int = 0

    def abilities(self) -> list[int]:
        return [self.reading, self.writing, self.listening, self.speaking]

    def minimum(self) -> int:
        return min(self.abilities()) if self.abilities() else 0


@dataclass
class SpouseProfile:
    education: str = "none"
    first_language: LanguageScores = field(default_factory=LanguageScores)
    canadian_experience_years: int = 0


@dataclass
class CrsProfile:
    """Everything the CRS grid needs. Absent fields score zero, never crash."""

    age: int | None = None
    education: str = "none"
    first_language: LanguageScores = field(default_factory=LanguageScores)
    second_language: LanguageScores = field(default_factory=LanguageScores)
    canadian_experience_years: int = 0
    foreign_experience_years: int = 0
    has_spouse: bool = False
    spouse: SpouseProfile | None = None

    # additional points
    provincial_nomination: bool = False
    sibling_in_canada: bool = False
    canadian_study_credential: str | None = None  # None | "one_or_two_year" | "three_year_plus"
    trades_certificate: bool = False

    def education_rank(self) -> int:
        try:
            return EDUCATION_ORDER.index(self.education)
        except ValueError:
            return 0


def _clamp_years(years: float | int | None, ceiling: int) -> int:
    if not years or years < 0:
        return 0
    return min(int(years), ceiling)


def _core_human_capital(p: CrsProfile) -> dict[str, int]:
    spouse = p.has_spouse

    age_points = 0
    if p.age is not None:
        if p.age >= 45:
            age_points = 0
        else:
            age_points = _AGE_POINTS.get(p.age, (0, 0))[1 if spouse else 0]

    education_points = _EDUCATION_POINTS.get(p.education, (0, 0))[1 if spouse else 0]

    first_lang = sum(_first_language_points(clb, spouse) for clb in p.first_language.abilities())
    first_lang = min(first_lang, 128 if spouse else 136)

    second_lang = sum(_second_language_points(clb) for clb in p.second_language.abilities())
    second_lang = min(second_lang, 22 if spouse else 24)

    cdn_years = _clamp_years(p.canadian_experience_years, 5)
    cdn_exp = _CANADIAN_EXPERIENCE_POINTS[cdn_years][1 if spouse else 0]

    return {
        "age": age_points,
        "education": education_points,
        "first_language": first_lang,
        "second_language": second_lang,
        "canadian_experience": cdn_exp,
    }


def _spouse_factors(p: CrsProfile) -> dict[str, int]:
    if not p.has_spouse or p.spouse is None:
        return {"spouse_education": 0, "spouse_language": 0, "spouse_canadian_experience": 0}

    s = p.spouse
    education = min(_SPOUSE_EDUCATION_POINTS.get(s.education, 0), 10)
    language = min(sum(_spouse_language_points(clb) for clb in s.first_language.abilities()), 20)
    experience = _SPOUSE_CANADIAN_EXPERIENCE_POINTS[_clamp_years(s.canadian_experience_years, 5)]

    return {
        "spouse_education": education,
        "spouse_language": language,
        "spouse_canadian_experience": experience,
    }


def _skill_transferability(p: CrsProfile) -> dict[str, int]:
    """Each sub-block caps at 50; the whole section caps at 100."""
    min_first = p.first_language.minimum()
    strong_language = min_first >= 9
    good_language = min_first >= 7
    cdn_years = _clamp_years(p.canadian_experience_years, 5)
    foreign_years = _clamp_years(p.foreign_experience_years, 3)

    has_post_secondary = p.education_rank() >= EDUCATION_ORDER.index("one_year_post_secondary")
    advanced_credential = p.education_rank() >= EDUCATION_ORDER.index("two_or_more_credentials")

    # Education x language
    edu_lang = 0
    if has_post_secondary and good_language:
        if strong_language:
            edu_lang = 50 if advanced_credential else 25
        else:
            edu_lang = 25 if advanced_credential else 13

    # Education x Canadian work experience
    edu_exp = 0
    if has_post_secondary and cdn_years >= 1:
        if cdn_years >= 2:
            edu_exp = 50 if advanced_credential else 25
        else:
            edu_exp = 25 if advanced_credential else 13

    education_block = min(edu_lang + edu_exp, 50)

    # Foreign experience x language
    foreign_lang = 0
    if foreign_years >= 1 and good_language:
        if strong_language:
            foreign_lang = 50 if foreign_years >= 3 else 25
        else:
            foreign_lang = 25 if foreign_years >= 3 else 13

    # Foreign experience x Canadian work experience
    foreign_exp = 0
    if foreign_years >= 1 and cdn_years >= 1:
        if cdn_years >= 2:
            foreign_exp = 50 if foreign_years >= 3 else 25
        else:
            foreign_exp = 25 if foreign_years >= 3 else 13

    foreign_block = min(foreign_lang + foreign_exp, 50)

    # Certificate of qualification (trades) x language
    trades_block = 0
    if p.trades_certificate:
        if good_language:
            trades_block = 50
        elif min_first >= 5:
            trades_block = 25

    total = min(education_block + foreign_block + trades_block, MAX_TRANSFERABILITY)

    return {
        "education_transferability": education_block,
        "foreign_experience_transferability": foreign_block,
        "trades_transferability": trades_block,
        "_total": total,
    }


def _additional_points(p: CrsProfile) -> dict[str, int]:
    french = 0
    # French bonus keys off NCLC 7+ across all four French abilities.
    if p.second_language.minimum() >= 7:
        french = 50 if p.first_language.minimum() >= 5 else 25

    study = 0
    if p.canadian_study_credential == "three_year_plus":
        study = 30
    elif p.canadian_study_credential == "one_or_two_year":
        study = 15

    return {
        "provincial_nomination": 600 if p.provincial_nomination else 0,
        "french_bonus": french,
        "canadian_study": study,
        "sibling_in_canada": 15 if p.sibling_in_canada else 0,
        # Retained explicitly so the zero is visible in the breakdown rather than
        # looking like an omission. Removed by IRCC on 2025-03-25.
        "arranged_employment": 0,
    }


@dataclass
class CrsResult:
    total: int
    core: int
    spouse: int
    transferability: int
    additional: int
    breakdown: dict[str, int]
    grid_version: str = GRID_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "core": self.core,
            "spouse": self.spouse,
            "transferability": self.transferability,
            "additional": self.additional,
            "breakdown": self.breakdown,
            "grid_version": self.grid_version,
        }


def calculate_crs(profile: CrsProfile) -> CrsResult:
    """Score a profile against the CRS grid. Never raises on partial input."""
    core_parts = _core_human_capital(profile)
    spouse_parts = _spouse_factors(profile)
    transfer_parts = _skill_transferability(profile)
    additional_parts = _additional_points(profile)

    core_cap = MAX_CORE_WITH_SPOUSE if profile.has_spouse else MAX_CORE_WITHOUT_SPOUSE
    core = min(sum(core_parts.values()), core_cap)
    spouse = min(sum(spouse_parts.values()), MAX_SPOUSE_FACTORS)
    transferability = transfer_parts["_total"]
    additional = min(sum(additional_parts.values()), MAX_ADDITIONAL)

    total = min(core + spouse + transferability + additional, MAX_TOTAL)

    breakdown = {
        **core_parts,
        **spouse_parts,
        **{k: v for k, v in transfer_parts.items() if not k.startswith("_")},
        **additional_parts,
    }

    return CrsResult(
        total=total,
        core=core,
        spouse=spouse,
        transferability=transferability,
        additional=additional,
        breakdown=breakdown,
    )


def profile_from_db(
    profile: dict[str, Any],
    canadian_months: int = 0,
    foreign_months: int = 0,
) -> CrsProfile:
    """Map a Supabase `profiles` row onto a CrsProfile.

    Unknown or missing fields degrade to zero-point defaults rather than guessing,
    so an incomplete profile produces an honest floor rather than an inflated score.
    """

    def lang(prefix: str) -> LanguageScores:
        return LanguageScores(
            reading=int(profile.get(f"{prefix}_reading") or 0),
            writing=int(profile.get(f"{prefix}_writing") or 0),
            listening=int(profile.get(f"{prefix}_listening") or 0),
            speaking=int(profile.get(f"{prefix}_speaking") or 0),
        )

    spouse_row = profile.get("spouse") or {}
    has_spouse = bool(profile.get("has_accompanying_spouse"))

    return CrsProfile(
        age=profile.get("age"),
        education=profile.get("education_level") or "none",
        first_language=lang("clb_en"),
        second_language=lang("nclc_fr"),
        canadian_experience_years=canadian_months // 12,
        foreign_experience_years=foreign_months // 12,
        has_spouse=has_spouse,
        spouse=(
            SpouseProfile(
                education=spouse_row.get("education_level") or "none",
                first_language=LanguageScores(
                    reading=int(spouse_row.get("clb_reading") or 0),
                    writing=int(spouse_row.get("clb_writing") or 0),
                    listening=int(spouse_row.get("clb_listening") or 0),
                    speaking=int(spouse_row.get("clb_speaking") or 0),
                ),
                canadian_experience_years=int(spouse_row.get("canadian_experience_years") or 0),
            )
            if has_spouse
            else None
        ),
        provincial_nomination=bool(profile.get("has_provincial_nomination")),
        sibling_in_canada=bool(profile.get("sibling_in_canada")),
        canadian_study_credential=profile.get("canadian_study_credential"),
        trades_certificate=bool(profile.get("trades_certificate")),
    )
