"""Service for parsing uploaded application log files."""

from __future__ import annotations

from pathlib import Path

from parsers.log_parser import LogParser


class LogParserService:
    """Read log files and return normalized API entries."""

    def __init__(self, parser: LogParser | None = None) -> None:
        self.parser = parser or LogParser()

    def parse_file(self, file_path: str | Path) -> list[dict[str, str | list[str] | None]]:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        return self.parser.parse(content)
