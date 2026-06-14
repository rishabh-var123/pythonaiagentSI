"""AI Solution Integrator Assistant FastAPI application."""

from __future__ import annotations

import shutil
import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from models import database
from parsers.flow_parser import FlowParser
from parsers.log_parser import LogParser
from services.flow_validation_service import FlowValidationService
from services.log_parser_service import LogParserService
from services.report_service import RCAReportService


BASE_DIR = Path(__file__).resolve().parents[1]
UPLOADS_DIR = BASE_DIR / "uploads"
FLOWS_DIR = UPLOADS_DIR / "flows"
LOGS_DIR = UPLOADS_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"

app = FastAPI(
    title="AI Solution Integrator Assistant",
    description="Upload flows and application logs, validate API execution, and generate RCA reports.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    for directory in (UPLOADS_DIR, FLOWS_DIR, LOGS_DIR, REPORTS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    database.init_db()


@app.get("/", response_class=HTMLResponse, tags=["Application"])
def home() -> str:
    return """
    <!doctype html>
    <html>
      <head><title>AI Solution Integrator Assistant</title></head>
      <body style="font-family: Arial, sans-serif; margin: 40px;">
        <h1>AI Solution Integrator Assistant</h1>
        <p>FastAPI service is running.</p>
        <ul>
          <li><a href="/docs">Swagger API documentation</a></li>
          <li><a href="/health">Health check</a></li>
          <li><a href="/api/history">History</a></li>
        </ul>
      </body>
    </html>
    """


@app.get("/health", tags=["Application"])
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "ai-solution-integrator-assistant"}


@app.post("/api/upload-flow", tags=["Upload Flow"])
def upload_flow(file: Annotated[UploadFile, File(description="Flow definition file")]) -> dict[str, Any]:
    saved_path = save_upload(file, FLOWS_DIR)
    content = read_text_safely(saved_path)
    apis = FlowParser().parse(content)
    upload = database.insert_upload(
        "flow",
        file.filename or saved_path.name,
        saved_path,
        {"api_count": len(apis), "apis": apis},
    )
    return {"message": "Flow uploaded successfully", "upload": upload}


@app.post("/api/upload-log", tags=["Upload Log"])
def upload_log(file: Annotated[UploadFile, File(description="Application log file")]) -> dict[str, Any]:
    saved_path = save_upload(file, LOGS_DIR)
    parsed_entries = LogParserService().parse_file(saved_path)
    upload = database.insert_upload(
        "log",
        file.filename or saved_path.name,
        saved_path,
        {"entry_count": len(parsed_entries), "entries": parsed_entries},
    )
    return {"message": "Log uploaded successfully", "upload": upload, "entries": parsed_entries}


@app.post("/api/validate-flow", tags=["Validation"])
def validate_flow(
    flow_upload_id: Annotated[int | None, Query(description="Flow upload ID. Defaults to latest flow upload.")] = None,
    log_upload_id: Annotated[int | None, Query(description="Log upload ID. Defaults to latest log upload.")] = None,
) -> dict[str, Any]:
    flow_upload = resolve_upload("flow", flow_upload_id)
    log_upload = resolve_upload("log", log_upload_id)

    summary = FlowValidationService().validate_files(flow_upload["path"], log_upload["path"])
    validation = database.insert_validation(flow_upload["id"], log_upload["id"], summary["status"], summary)
    return {"message": "Flow validation completed", "validation": validation}


@app.post("/api/rca-report", tags=["RCA Report"])
def create_rca_report(
    validation_id: Annotated[
        int | None,
        Query(description="Validation ID. Defaults to latest validation."),
    ] = None,
) -> dict[str, Any]:
    validation = database.get_validation(validation_id) if validation_id else database.get_latest_validation()
    if not validation:
        raise HTTPException(status_code=404, detail="No validation result found")

    report = RCAReportService().build_report(validation)
    saved_report = database.insert_report(validation.get("id"), str(report["status"]), report)
    report_file = REPORTS_DIR / f"rca-report-{saved_report['id']}.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"message": "RCA report generated", "report": saved_report}


@app.get("/api/history", tags=["History"])
def history(limit: Annotated[int, Query(ge=1, le=200)] = 50) -> dict[str, Any]:
    return {"items": database.list_history(limit)}


def save_upload(file: UploadFile, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    filename = Path(file.filename or "upload.txt").name
    target = unique_path(directory / filename)
    with target.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return target


def read_text_safely(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    for index in range(1, 10_000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise HTTPException(status_code=500, detail="Could not create a unique upload filename")


def resolve_upload(upload_type: str, upload_id: int | None) -> dict[str, Any]:
    upload = database.get_upload(upload_id) if upload_id else database.get_latest_upload(upload_type)
    if not upload or upload["type"] != upload_type:
        raise HTTPException(status_code=404, detail=f"No {upload_type} upload found")
    return upload
