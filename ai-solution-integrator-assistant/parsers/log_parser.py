"""Parser for application logs that contain HTTP API request/response lines."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable


HTTP_API_PATTERN = re.compile(
    r"\bHTTP\s+(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(?P<path>/[^\s?]+)",
    re.IGNORECASE,
)
TIMESTAMP_PATTERN = re.compile(r"\b(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\b")
STATUS_PATTERN = re.compile(r"\b(?P<status>SUCCESS|FAILED|FAILURE|ERROR|OK)\b", re.IGNORECASE)
ERROR_PATTERN = re.compile(r"\b(ERROR|EXCEPTION|FAILED|FAILURE)\b[:\s-]*(?P<message>.*)", re.IGNORECASE)


@dataclass
class LogEntry:
    """Normalized API log entry."""

    api: str
    status: str = "UNKNOWN"
    timestamp: str | None = None
    request_timestamp: str | None = None
    response_timestamp: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, str | list[str] | None]:
        return {
            "api": self.api,
            "status": self.status,
            "timestamp": self.timestamp,
            "request_timestamp": self.request_timestamp,
            "response_timestamp": self.response_timestamp,
            "errors": self.errors,
        }


class LogParser:
    """Extract API activity from application log lines."""

    def parse(self, content: str) -> list[dict[str, str | list[str] | None]]:
        return [entry.to_dict() for entry in self.parse_lines(content.splitlines())]

    def parse_lines(self, lines: Iterable[str]) -> list[LogEntry]:
        entries: list[LogEntry] = []
        current_entry: LogEntry | None = None

        for line in lines:
            timestamp = self._extract_timestamp(line)
            api = self._extract_api_name(line)

            if api:
                current_entry = LogEntry(
                    api=api,
                    timestamp=timestamp,
                    request_timestamp=timestamp,
                )
                self._apply_status(line, current_entry)
                self._apply_error(line, current_entry)
                entries.append(current_entry)
                continue

            if current_entry is None:
                continue

            if timestamp and self._looks_like_response(line):
                current_entry.response_timestamp = timestamp

            self._apply_status(line, current_entry)
            self._apply_error(line, current_entry)

        return entries

    def _extract_api_name(self, line: str) -> str | None:
        match = HTTP_API_PATTERN.search(line)
        if not match:
            return None

        path = match.group("path").rstrip("/")
        return path.rsplit("/", maxsplit=1)[-1].lower()

    def _extract_timestamp(self, line: str) -> str | None:
        match = TIMESTAMP_PATTERN.search(line)
        return match.group("timestamp") if match else None

    def _apply_status(self, line: str, entry: LogEntry) -> None:
        match = STATUS_PATTERN.search(line)
        if not match:
            return

        status = match.group("status").upper()
        if status in {"OK"}:
            status = "SUCCESS"
        elif status in {"FAILED", "FAILURE", "ERROR"}:
            status = "FAILED"

        entry.status = status

    def _apply_error(self, line: str, entry: LogEntry) -> None:
        match = ERROR_PATTERN.search(line)
        if not match:
            return

        message = match.group("message").strip()
        if message:
            entry.errors.append(message)

    def _looks_like_response(self, line: str) -> bool:
        return bool(re.search(r"\b(response|responded|completed|status)\b", line, re.IGNORECASE))
