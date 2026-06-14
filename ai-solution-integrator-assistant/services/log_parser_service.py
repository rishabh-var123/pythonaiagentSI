"""Service for parsing uploaded application log files."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from parsers.log_parser import LogParser


class LogParserService:
    """Read log files and return normalized API entries."""

    def __init__(self, parser: LogParser | None = None) -> None:
        self.parser = parser or LogParser()

    def parse_file(self, file_path: str | Path) -> list[dict[str, str | list[str] | None]]:
        path = Path(file_path)
        if path.suffix.lower() == ".zip":
            return self._parse_zip(path)

        content = path.read_text(encoding="utf-8", errors="replace")
        return self.parser.parse(content)

    def _parse_zip(self, file_path: Path) -> list[dict[str, str | list[str] | None]]:
        entries: list[dict[str, str | list[str] | None]] = []
        with ZipFile(file_path) as archive:
            for name in archive.namelist():
                if not name.lower().endswith((".log", ".txt")):
                    continue
                content = archive.read(name).decode("utf-8", errors="ignore")
                entries.extend(self.parser.parse(content))
        return entries
