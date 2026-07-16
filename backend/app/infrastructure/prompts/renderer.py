import re
from typing import Any


class PromptRenderer:
    """Renders {{variable}} placeholders in prompt templates."""

    _pattern = re.compile(r"\{\{\s*(\w+)\s*\}\}")

    def render(self, template: str, variables: dict[str, Any]) -> str:
        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            value = variables.get(key, "")
            if value is None:
                return ""
            if isinstance(value, (dict, list)):
                import json

                return json.dumps(value, indent=2)
            return str(value)

        return self._pattern.sub(replace, template)
