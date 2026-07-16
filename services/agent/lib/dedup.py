"""Dedupe helpers — company + normalized title + city."""

from __future__ import annotations

import hashlib
import re


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def compute_dedupe_hash(company: str, title: str, province: str, city: str) -> str:
    parts = [
        normalize_text(company),
        normalize_text(title),
        (province or "").strip().upper(),
        normalize_text(city),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()
