import tempfile
import unittest
from pathlib import Path

from parsers.log_parser import LogParser
from services.log_parser_service import LogParserService


class LogParserTest(unittest.TestCase):
    def test_extracts_api_status_and_timestamp_from_single_request_line(self):
        content = "2026-05-04 14:28:13 HTTP POST /lwam/getaccountholderinfo SUCCESS"

        result = LogParser().parse(content)

        self.assertEqual(
            result,
            [
                {
                    "api": "getaccountholderinfo",
                    "status": "SUCCESS",
                    "timestamp": "2026-05-04 14:28:13",
                    "request_timestamp": "2026-05-04 14:28:13",
                    "response_timestamp": None,
                    "errors": [],
                }
            ],
        )

    def test_extracts_response_timestamp_status_and_errors(self):
        content = "\n".join(
            [
                "2026-05-04 14:28:13 INFO HTTP POST /lwam/getaccountholderinfo",
                "2026-05-04 14:28:15 ERROR Response FAILED: Account holder not found",
            ]
        )

        result = LogParser().parse(content)

        self.assertEqual(result[0]["api"], "getaccountholderinfo")
        self.assertEqual(result[0]["status"], "FAILED")
        self.assertEqual(result[0]["timestamp"], "2026-05-04 14:28:13")
        self.assertEqual(result[0]["request_timestamp"], "2026-05-04 14:28:13")
        self.assertEqual(result[0]["response_timestamp"], "2026-05-04 14:28:15")
        self.assertEqual(result[0]["errors"], ["Response FAILED: Account holder not found"])

    def test_service_parses_application_log_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "application.log"
            log_file.write_text(
                "2026-05-04 14:28:13 HTTP GET /accounts/profile OK",
                encoding="utf-8",
            )

            result = LogParserService().parse_file(log_file)

        self.assertEqual(result[0]["api"], "profile")
        self.assertEqual(result[0]["status"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()
