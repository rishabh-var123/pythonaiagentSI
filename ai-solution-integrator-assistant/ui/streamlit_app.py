"""Business Streamlit UI for the AI Solution Integrator Assistant."""

from __future__ import annotations

import base64
import os
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
import streamlit as st


DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
FLOW_TYPES = ["svg", "png", "pdf", "json"]
LOG_TYPES = ["log", "txt", "zip"]


def main() -> None:
    st.set_page_config(page_title="AI Solution Integrator Assistant", page_icon="AI", layout="wide")
    init_state()
    render_styles()

    st.sidebar.title("AI Solution Integrator")
    st.sidebar.caption("Business validation UI")
    st.session_state.api_base_url = st.sidebar.text_input("Backend API", st.session_state.api_base_url)
    page = st.sidebar.radio(
        "Navigation",
        ["Upload Flow", "Upload Log", "Validate Flow", "RCA Report", "Dashboard", "History"],
    )

    pages = {
        "Upload Flow": upload_flow_page,
        "Upload Log": upload_log_page,
        "Validate Flow": validate_flow_page,
        "RCA Report": rca_report_page,
        "Dashboard": dashboard_page,
        "History": history_page,
    }
    pages[page]()


def init_state() -> None:
    defaults = {
        "api_base_url": DEFAULT_API_BASE_URL,
        "flow_file": None,
        "log_file": None,
        "flow_upload_response": None,
        "log_upload_response": None,
        "latest_validation": None,
        "latest_report": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def render_styles() -> None:
    st.markdown(
        """
        <style>
          .block-container { padding-top: 1.25rem; max-width: 1280px; }
          [data-testid="stMetricValue"] { font-size: 1.65rem; }
          div[data-testid="stFileUploader"] section { border-radius: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def api_url(endpoint: str) -> str:
    return f"{st.session_state.api_base_url.rstrip('/')}{endpoint}"


def api_get(endpoint: str) -> dict[str, Any]:
    try:
        response = requests.get(api_url(endpoint), timeout=15)
        return parse_response(response)
    except requests.RequestException as exc:
        return {"error": str(exc)}


def api_post(endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        response = requests.post(api_url(endpoint), params=params or {}, timeout=90)
        return parse_response(response)
    except requests.RequestException as exc:
        st.error(f"Backend request failed: {exc}")
        return {"error": str(exc)}


def api_upload(endpoint: str, file_record: dict[str, Any]) -> dict[str, Any]:
    files = {"file": (file_record["name"], file_record["bytes"], file_record["type"])}
    try:
        response = requests.post(api_url(endpoint), files=files, timeout=90)
        return parse_response(response)
    except requests.RequestException as exc:
        st.error(f"Upload failed: {exc}")
        return {"error": str(exc)}


def parse_response(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": response.text}

    if response.ok:
        return payload

    st.error(payload.get("detail", "Backend request failed"))
    return payload


def store_file(state_key: str, uploaded_file: Any) -> None:
    if not uploaded_file:
        return
    st.session_state[state_key] = {
        "name": uploaded_file.name,
        "bytes": uploaded_file.getvalue(),
        "type": uploaded_file.type or "application/octet-stream",
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def upload_flow_page() -> None:
    render_header("Upload Flow Page", "Upload a flow artifact for validation.")
    uploaded_file = st.file_uploader("Flow file", type=FLOW_TYPES, key="flow_uploader")
    store_file("flow_file", uploaded_file)

    flow_file = st.session_state.flow_file
    render_file_summary(flow_file, "Supported formats: .svg, .png, .pdf, .json")
    render_preview(flow_file)

    if flow_file and st.button("Upload Flow", type="primary", use_container_width=True):
        response = api_upload("/api/upload-flow", flow_file)
        st.session_state.flow_upload_response = response
        if response.get("upload"):
            st.success("Flow uploaded successfully.")
        st.json(response)


def upload_log_page() -> None:
    render_header("Upload Log Page", "Upload execution logs for comparison.")
    uploaded_file = st.file_uploader("Log file", type=LOG_TYPES, key="log_uploader")
    store_file("log_file", uploaded_file)

    log_file = st.session_state.log_file
    render_file_summary(log_file, "Supported formats: .log, .txt, .zip")
    render_preview(log_file)

    if log_file and st.button("Upload Log", type="primary", use_container_width=True):
        response = api_upload("/api/upload-log", log_file)
        st.session_state.log_upload_response = response
        if response.get("upload"):
            st.success("Log uploaded successfully.")
        st.json(response)


def validate_flow_page() -> None:
    render_header("Validate Flow Page", "Review uploaded inputs and call the backend validator.")

    left, right = st.columns(2)
    with left:
        st.subheader("Uploaded Flow")
        render_upload_response(st.session_state.flow_upload_response, "flow")
        render_preview(st.session_state.flow_file, compact=True)
    with right:
        st.subheader("Uploaded Log")
        render_upload_response(st.session_state.log_upload_response, "log")
        render_preview(st.session_state.log_file, compact=True)

    st.divider()
    if st.button("Validate", type="primary", use_container_width=True):
        flow_id = get_upload_id(st.session_state.flow_upload_response)
        log_id = get_upload_id(st.session_state.log_upload_response)
        if not flow_id or not log_id:
            st.error("Upload both flow and log files before validation.")
            return

        response = api_post("/api/validate-flow", {"flow_upload_id": flow_id, "log_upload_id": log_id})
        st.session_state.latest_validation = response
        if response.get("validation"):
            st.success("Validation completed.")

    render_validation(st.session_state.latest_validation)


def rca_report_page() -> None:
    render_header("RCA Report Page", "Generate RCA from the latest validation result.")

    validation_id = get_validation_id(st.session_state.latest_validation)
    if not validation_id:
        st.info("Run validation before generating RCA.")
        return

    if st.button("Generate RCA", type="primary", use_container_width=True):
        response = api_post("/api/rca-report", {"validation_id": validation_id})
        st.session_state.latest_report = response
        if response.get("report"):
            st.success("RCA report generated.")

    render_report(st.session_state.latest_report)


def dashboard_page() -> None:
    render_header("Dashboard Page", "Validation summary from backend history.")
    history = get_history(200)
    validations = [item for item in history if item.get("event_type") == "validation"]
    passed = len([item for item in validations if item.get("status") == "SUCCESS"])
    failed = len([item for item in validations if item.get("status") == "FAILED"])

    cols = st.columns(3)
    cols[0].metric("Total Validations", len(validations))
    cols[1].metric("Passed", passed)
    cols[2].metric("Failed", failed)

    st.subheader("Latest Activity")
    render_history_table(history[:10])


def history_page() -> None:
    render_header("History Page", "View uploads, validations, and RCA reports.")
    history = get_history(100)
    render_history_table(history)

    if history:
        labels = [f"{item['event_type']} #{item['id']} - {item['created_at']}" for item in history]
        selected = st.selectbox("History item", labels)
        selected_item = history[labels.index(selected)]
        st.subheader("Selected Details")
        st.json(selected_item)


def render_header(title: str, caption: str) -> None:
    st.title(title)
    st.caption(caption)


def render_file_summary(file_record: dict[str, Any] | None, empty_text: str) -> None:
    if not file_record:
        st.info(empty_text)
        return

    cols = st.columns(3)
    cols[0].metric("File", file_record["name"])
    cols[1].metric("Size", f"{len(file_record['bytes']) / 1024:.1f} KB")
    cols[2].metric("Selected", file_record["uploaded_at"])


def render_upload_response(response: dict[str, Any] | None, upload_type: str) -> None:
    upload = (response or {}).get("upload")
    if not upload:
        st.info(f"No {upload_type} uploaded to backend yet.")
        return

    cols = st.columns(3)
    cols[0].metric("Upload ID", upload.get("id", "N/A"))
    cols[1].metric("Filename", upload.get("filename", "N/A"))
    cols[2].metric("Created", upload.get("created_at", "N/A"))


def render_preview(file_record: dict[str, Any] | None, compact: bool = False) -> None:
    if not file_record:
        return

    suffix = Path(file_record["name"]).suffix.lower()
    data = file_record["bytes"]
    if not compact:
        st.subheader("Preview")

    if suffix == ".svg":
        encoded = base64.b64encode(data).decode("ascii")
        st.markdown(
            f'<img src="data:image/svg+xml;base64,{encoded}" style="width:100%;max-height:420px;object-fit:contain;border:1px solid #d0d7de;border-radius:8px;padding:8px;" />',
            unsafe_allow_html=True,
        )
    elif suffix == ".png":
        st.image(data, use_container_width=True)
    elif suffix == ".pdf":
        encoded = base64.b64encode(data).decode("ascii")
        height = 420 if compact else 620
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{encoded}" width="100%" height="{height}" style="border:1px solid #d0d7de;border-radius:8px;"></iframe>',
            unsafe_allow_html=True,
        )
    elif suffix == ".zip":
        render_zip_preview(data)
    else:
        text = data.decode("utf-8", errors="replace")
        height = 180 if compact else 300
        st.text_area("Text preview", text[:20000], height=height, disabled=True)


def render_zip_preview(data: bytes) -> None:
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            rows = [
                {"File": item.filename, "Compressed Bytes": item.compress_size, "Bytes": item.file_size}
                for item in archive.infolist()
            ]
        st.dataframe(rows, hide_index=True, use_container_width=True)
    except zipfile.BadZipFile:
        st.error("The uploaded file is not a valid ZIP archive.")


def render_validation(response: dict[str, Any] | None) -> None:
    validation = (response or {}).get("validation")
    if not validation:
        return

    summary = validation.get("summary", {})
    expected = summary.get("expected_apis", [])
    observed = summary.get("observed_apis", [])
    missing = summary.get("missing_apis", [])
    unexpected = summary.get("unexpected_apis", [])
    compliance = calculate_compliance(expected, missing)

    st.subheader("Validation Results")
    cols = st.columns(5)
    cols[0].metric("Status", validation.get("status", "N/A"))
    cols[1].metric("Compliance", f"{compliance:.1f}%")
    cols[2].metric("Expected", len(expected))
    cols[3].metric("Observed", len(observed))
    cols[4].metric("Missing", len(missing))

    st.write("Expected Flow")
    st.json(expected)
    st.write("Observed Log APIs")
    st.json(observed)
    st.write("Missing APIs")
    st.json(missing)
    st.write("Unexpected APIs")
    st.json(unexpected)


def render_report(response: dict[str, Any] | None) -> None:
    saved_report = (response or {}).get("report")
    if not saved_report:
        return

    report = saved_report.get("report", {})
    evidence = report.get("evidence", {})

    st.subheader("RCA Results")
    cols = st.columns(3)
    cols[0].metric("Report ID", saved_report.get("id", "N/A"))
    cols[1].metric("Validation ID", saved_report.get("validation_id", "N/A"))
    cols[2].metric("Status", saved_report.get("status", "N/A"))

    st.write("Root Causes")
    st.json(report.get("root_causes", []))
    st.write("Recommended Actions")
    st.json(report.get("recommended_actions", []))
    st.write("Evidence")
    st.json(evidence)


def render_history_table(history: list[dict[str, Any]]) -> None:
    if not history:
        st.info("No history found.")
        return

    st.dataframe(
        [
            {
                "Created At": item.get("created_at"),
                "Event": item.get("event_type"),
                "Status": item.get("status"),
                "Title": item.get("title"),
            }
            for item in history
        ],
        hide_index=True,
        use_container_width=True,
    )


def get_history(limit: int) -> list[dict[str, Any]]:
    payload = api_get(f"/api/history?limit={limit}")
    return payload.get("items", [])


def get_upload_id(response: dict[str, Any] | None) -> int | None:
    upload = (response or {}).get("upload", {})
    return upload.get("id")


def get_validation_id(response: dict[str, Any] | None) -> int | None:
    validation = (response or {}).get("validation", {})
    return validation.get("id")


def calculate_compliance(expected: list[str], missing: list[str]) -> float:
    if not expected:
        return 100.0 if not missing else 0.0
    return ((len(expected) - len(missing)) / len(expected)) * 100


if __name__ == "__main__":
    main()
