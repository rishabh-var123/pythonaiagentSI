"""Extract API names from uploaded flow definition files."""

from __future__ import annotations

import re


HTTP_PATH_PATTERN = re.compile(
    r"\b(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(?P<path>/[^\s,;]+)",
    re.IGNORECASE,
)
API_KEY_PATTERN = re.compile(r"\bapi\s*[:=]\s*['\"]?(?P<api>[a-zA-Z0-9_-]+)", re.IGNORECASE)


class FlowParser:
    """Parse simple text, JSON-like, YAML-like, or log-style flow files."""

    def parse(self, content: str) -> list[str]:
        apis: set[str] = set()

        for match in HTTP_PATH_PATTERN.finditer(content):
            apis.add(match.group("path").rstrip("/").rsplit("/", maxsplit=1)[-1].lower())

        for match in API_KEY_PATTERN.finditer(content):
            apis.add(match.group("api").lower())

        return sorted(apis)
