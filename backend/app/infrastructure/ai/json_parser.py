import json
import re


def extract_json_object(text: str) -> dict:
    """Parse JSON from an LLM response, including fenced code blocks."""
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fence_match:
        return json.loads(fence_match.group(1))

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(stripped[start : end + 1])

    raise ValueError("No JSON object found in LLM response")
