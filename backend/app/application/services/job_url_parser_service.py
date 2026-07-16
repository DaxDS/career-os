import json
import re
import urllib.error
import urllib.request
from html import unescape
from typing import Any

from app.application.ports.llm import LLMMessage, ModelRouterPort
from app.domain.enums import AICapability
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 CareerOS/1.0"
)
_MAX_HTML_CHARS = 14_000


def _fetch_url(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept-Language": "en-CA,en"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def _html_to_text(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(html)).strip()


class JobUrlParserService:
    def __init__(self, router: ModelRouterPort):
        self._router = router

    def parse(self, url: str) -> dict[str, Any]:
        try:
            raw_html = _fetch_url(url)
        except urllib.error.URLError as exc:
            raise ValueError(f"Could not fetch URL: {exc}") from exc

        page_text = _html_to_text(raw_html)[:_MAX_HTML_CHARS]
        prompt = f"""Extract job posting fields from this page. URL: {url}

Page text:
{page_text}

Respond with JSON only:
{{
  "title": "job title",
  "company": "employer name",
  "description": "full job description text",
  "location": "city, province or country",
  "location_province": "2-letter Canadian province code if applicable else empty string"
}}"""

        response = self._router.complete_for_capability(
            AICapability.STRUCTURED_OUTPUT,
            [LLMMessage(role="user", content=prompt)],
        )
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        return {
            "title": str(data.get("title") or "").strip(),
            "company": str(data.get("company") or "").strip(),
            "description": str(data.get("description") or "").strip(),
            "location": str(data.get("location") or "").strip(),
            "location_province": str(data.get("location_province") or "ON").strip().upper()[:2],
            "source_url": url,
        }
