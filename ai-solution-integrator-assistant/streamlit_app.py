"""Streamlit frontend for the AI Solution Integrator Assistant."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
BASE_DIR = Path(__file__).resolve().parent
FLOW_UPLOAD_DIR = BASE_DIR / "uploads" / "flows"
LOG_UPLOAD_DIR = BASE_DIR / "uploads" / "logs"


def main() -> None:
    st.set_page_config(page_title="AI Solution Integrator Assistant", layout="wide")
    ensure_upload_dirs()
    render_styles()

    st.sidebar.title("Menu")
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Upload Flow", "Upload Logs", "Validate Flow", "RCA Report", "History"],
        label_visibility="collapsed",
    )

    st.title("AI Solution Integrator Assistant")

    if page == "Dashboard":
        render_dashboard()
    elif page == "Upload Flow":
        render_upload_flow()
    elif page == "Upload Logs":
        render_upload_logs()
    elif page == "Validate Flow":
        render_validate_flow()
    elif page == "RCA Report":
        render_rca_report()
    elif page == "History":
        render_history()


def render_styles() -> None:
    st.markdown(
        """
        <style>
          .block-container { padding-top: 1.25rem; max-width: 1280px; }
          [data-testid="stMetricValue"] { font-size: 1.7rem; }
          .section-note { color: #5b6472; font-size: 0.92rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard() -> None:
    st.subheader("Dashboard")
    health = api_get("/health")
    history = get_history()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("API Status", health.get("status", "unavailable"))
    col2.metric("Activities", len(history))
    col3.metric("Validations", count_events(history, "validation"))
    col4.metric("Reports", count_events(history, "report"))

    st.divider()
    st.subheader("Recent Activity")
    render_history_table(history[:10])


def render_upload_flow() -> None:
    st.subheader("Upload Flow")
    uploaded_file = st.file_uploader("Select flow file", type=["svg", "png", "jpg", "pdf", "json"])

    if uploaded_file and st.button("Upload Flow", use_container_width=True):
        saved_path = save_streamlit_upload(uploaded_file, FLOW_UPLOAD_DIR)
        response = api_upload("/api/upload-flow", uploaded_file)
        st.session_state["flow_file"] = uploaded_file.name
        st.session_state["flow_upload"] = response
        st.success(f"Flow file stored in uploads/flows/: {saved_path.name}")
        st.json(response)


def render_upload_logs() -> None:
    st.subheader("Upload Logs")
    uploaded_file = st.file_uploader("Select log file", type=["log", "txt", "zip"])

    if uploaded_file and st.button("Upload Logs", use_container_width=True):
        saved_path = save_streamlit_upload(uploaded_file, LOG_UPLOAD_DIR)
        response = api_upload("/api/upload-log", uploaded_file)
        st.session_state["log_file"] = uploaded_file.name
        st.session_state["log_upload"] = response
        st.success(f"Log file stored in uploads/logs/: {saved_path.name}")
        st.json(response)


def render_validate_flow() -> None:
    st.subheader("Validate Flow")
    st.write(f"Flow File Selected: {selected_filename('flow')}")
    st.write(f"Log File Selected: {selected_filename('log')}")

    if st.button("Validate Flow", use_container_width=True):
        response = api_post("/api/validate-flow")
        st.session_state["latest_validation"] = response

    validation = st.session_state.get("latest_validation")
    if validation:
        summary = validation.get("validation", {}).get("summary", {})
        expected = summary.get("expected_apis", [])
        actual = summary.get("observed_apis", [])
        missing = summary.get("missing_apis", [])
        compliance = calculate_compliance(expected, missing)
        status = summary.get("status") or validation.get("validation", {}).get("status", "UNKNOWN")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Expected Flow", len(expected))
        col2.metric("Actual Flow", len(actual))
        col3.metric("Missing Steps", len(missing))
        col4.metric("Compliance Percentage", f"{compliance:.1f}%")

        st.metric("Status", status)
        st.write("Expected Flow")
        st.json(expected)
        st.write("Actual Flow")
        st.json(actual)
        st.write("Missing Steps")
        st.json(missing)


def render_rca_report() -> None:
    st.subheader("RCA Report")

    if st.button("Generate RCA", use_container_width=True):
        st.session_state["latest_report"] = api_post("/api/rca-report")

    report_response = st.session_state.get("latest_report")
    if report_response:
        report = report_response.get("report", {}).get("report", {})
        evidence = report.get("evidence", {})
        root_causes = report.get("root_causes", [])
        recommendations = report.get("recommended_actions", [])

        st.write("Root Cause")
        st.json(root_causes)
        st.write("Missing APIs")
        st.json(evidence.get("missing_apis", []))
        st.write("Owner Team")
        st.write(infer_owner_team(evidence))
        st.write("Recommendations")
        st.json(recommendations)


def render_history() -> None:
    st.subheader("History")
    history = get_history(limit=100)
    render_history_table(history)

    if history:
        st.write("Selected Details")
        selected_id = st.selectbox(
            "History item",
            [f"{item['event_type']} #{item['id']} - {item['created_at']}" for item in history],
        )
        selected_index = [f"{item['event_type']} #{item['id']} - {item['created_at']}" for item in history].index(
            selected_id
        )
        st.json(history[selected_index])


def render_history_table(history: list[dict[str, Any]]) -> None:
    if not history:
        st.info("No previous validations or reports found.")
        return

    st.dataframe(
        [
            {
                "Created At": item.get("created_at"),
                "Type": item.get("event_type"),
                "Status": item.get("status"),
                "Title": item.get("title"),
            }
            for item in history
        ],
        hide_index=True,
        use_container_width=True,
    )


def ensure_upload_dirs() -> None:
    FLOW_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    LOG_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_streamlit_upload(uploaded_file: Any, directory: Path) -> Path:
    safe_name = Path(uploaded_file.name).name
    target = unique_path(directory / safe_name)
    target.write_bytes(uploaded_file.getvalue())
    return target


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 10_000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("Unable to create a unique upload filename")


def api_upload(endpoint: str, uploaded_file: Any) -> dict[str, Any]:
    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
    response = requests.post(f"{API_BASE_URL}{endpoint}", files=files, timeout=60)
    return parse_response(response)


def api_post(endpoint: str) -> dict[str, Any]:
    response = requests.post(f"{API_BASE_URL}{endpoint}", timeout=60)
    return parse_response(response)


def api_get(endpoint: str) -> dict[str, Any]:
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
        return parse_response(response)
    except requests.RequestException as exc:
        return {"status": "unavailable", "error": str(exc)}


def parse_response(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": response.text}

    if response.ok:
        return payload

    st.error(payload.get("detail", "Backend request failed"))
    return payload


def get_history(limit: int = 50) -> list[dict[str, Any]]:
    payload = api_get(f"/api/history?limit={limit}")
    return payload.get("items", [])


def count_events(history: list[dict[str, Any]], event_type: str) -> int:
    return len([item for item in history if item.get("event_type") == event_type])


def selected_filename(file_type: str) -> str:
    session_key = f"{file_type}_file"
    if session_key in st.session_state:
        return st.session_state[session_key]

    upload = st.session_state.get(f"{file_type}_upload", {}).get("upload", {})
    return upload.get("filename", "None")


def calculate_compliance(expected: list[str], missing: list[str]) -> float:
    if not expected:
        return 100.0 if not missing else 0.0
    return ((len(expected) - len(missing)) / len(expected)) * 100


def infer_owner_team(evidence: dict[str, Any]) -> str:
    if evidence.get("missing_apis"):
        return "Integration Team"
    if evidence.get("failed_entries") or evidence.get("error_entries"):
        return "Application Support Team"
    return "Platform Team"


if __name__ == "__main__":
    main()
