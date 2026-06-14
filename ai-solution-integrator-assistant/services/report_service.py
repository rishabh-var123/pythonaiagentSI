"""RCA report generation service."""

from __future__ import annotations

from typing import Any


class RCAReportService:
    """Generate a concise RCA report from a validation summary."""

    def build_report(self, validation: dict[str, Any]) -> dict[str, Any]:
        summary = validation.get("summary", {})
        causes: list[str] = []
        actions: list[str] = []

        if summary.get("missing_apis"):
            causes.append("Expected APIs were not found in the uploaded application log.")
            actions.append("Verify that the flow was executed completely and the correct log file was uploaded.")

        if summary.get("failed_entries"):
            causes.append("One or more API calls completed with a failed status.")
            actions.append("Review failed API entries and upstream service responses.")

        if summary.get("error_entries"):
            causes.append("Error or exception lines were detected in the log response path.")
            actions.append("Inspect error messages and correlate them with request and response timestamps.")

        if not causes:
            causes.append("No blocking issue was detected in the latest validation.")
            actions.append("Archive the validation result or continue with downstream checks.")

        return {
            "validation_id": validation.get("id"),
            "status": validation.get("status"),
            "root_causes": causes,
            "recommended_actions": actions,
            "evidence": {
                "missing_apis": summary.get("missing_apis", []),
                "failed_entries": summary.get("failed_entries", []),
                "error_entries": summary.get("error_entries", []),
            },
        }
