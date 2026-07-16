import pytest

from app.infrastructure.ai.json_parser import extract_json_object


def test_parses_raw_json():
    result = extract_json_object('{"role_family": "it", "confidence": 0.9}')
    assert result["role_family"] == "it"


def test_parses_fenced_json():
    text = 'Here is the result:\n```json\n{"role_family": "production"}\n```'
    result = extract_json_object(text)
    assert result["role_family"] == "production"


def test_raises_when_no_json():
    with pytest.raises(ValueError, match="No JSON"):
        extract_json_object("no structured output here")
