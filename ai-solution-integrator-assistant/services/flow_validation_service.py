"""Flow validation service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from parsers.flow_parser import FlowParser
from parsers.log_parser import LogParser
from services.log_parser_service import LogParserService


class FlowValidationService:
    """Compare APIs expected by a flow with APIs observed in logs."""

    def __init__(self, flow_parser: FlowParser | None = None, log_parser: LogParser | None = None) -> None:
        self.flow_parser = flow_parser or FlowParser()
        self.log_parser = log_parser or LogParser()

    def validate_files(self, flow_path: str | Path, log_path: str | Path) -> dict[str, Any]:
        flow_content = Path(flow_path).read_text(encoding="utf-8", errors="replace")
        expected_apis = self.flow_parser.parse(flow_content)
        log_entries = LogParserService(self.log_parser).parse_file(log_path)
        observed_apis = sorted({str(entry["api"]) for entry in log_entries if entry.get("api")})

        missing_apis = sorted(set(expected_apis) - set(observed_apis))
        unexpected_apis = sorted(set(observed_apis) - set(expected_apis))
        failed_entries = [entry for entry in log_entries if entry.get("status") not in {"SUCCESS", "UNKNOWN"}]
        error_entries = [entry for entry in log_entries if entry.get("errors")]

        status = "SUCCESS"
        if missing_apis or failed_entries or error_entries:
            status = "FAILED"
        elif unexpected_apis:
            status = "WARNING"

        return {
            "status": status,
            "expected_apis": expected_apis,
            "observed_apis": observed_apis,
            "missing_apis": missing_apis,
            "unexpected_apis": unexpected_apis,
            "failed_entries": failed_entries,
            "error_entries": error_entries,
            "total_log_entries": len(log_entries),
        }
