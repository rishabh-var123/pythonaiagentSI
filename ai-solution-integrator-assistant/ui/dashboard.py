"""Streamlit dashboard for the AI Solution Integrator Assistant."""

from __future__ import annotations

import os

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


st.set_page_config(page_title="Flow Validation Agent", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.25rem; }
      [data-testid="stMetricValue"] { font-size: 1.6rem; }
      .status-ok { color: #146c43; font-weight: 700; }
      .status-fail { color: #b42318; font-weight: 700; }
      .status-warn { color: #8a5a00; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Flow Validation Agent")

health_col, docs_col = st.columns([3, 1])
with health_col:
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=5).json()
        st.caption(f"API: {health['status']} at {API_BASE_URL}")
    except requests.RequestException:
        st.caption(f"API unavailable at {API_BASE_URL}")
with docs_col:
    st.link_button("Swagger", f"{API_BASE_URL}/docs")

upload_col, action_col = st.columns([1, 1])

with upload_col:
    st.subheader("Inputs")
    flow_file = st.file_uploader("Flow file", type=["txt", "json", "yaml", "yml", "log"])
    log_file = st.file_uploader("Application log", type=["txt", "log"])

    if st.button("Upload Selected Files", use_container_width=True):
        if flow_file:
            response = requests.post(
                f"{API_BASE_URL}/api/upload-flow",
                files={"file": (flow_file.name, flow_file.getvalue())},
                timeout=30,
            )
            st.session_state["flow_upload"] = response.json()
        if log_file:
            response = requests.post(
                f"{API_BASE_URL}/api/upload-log",
                files={"file": (log_file.name, log_file.getvalue())},
                timeout=30,
            )
            st.session_state["log_upload"] = response.json()
        st.success("Upload complete")

with action_col:
    st.subheader("Validation")
    if st.button("Validate Flow", use_container_width=True):
        response = requests.post(f"{API_BASE_URL}/api/validate-flow", timeout=30)
        st.session_state["validation"] = response.json()

    if st.button("Generate RCA Report", use_container_width=True):
        response = requests.post(f"{API_BASE_URL}/api/rca-report", timeout=30)
        st.session_state["report"] = response.json()

    validation = st.session_state.get("validation", {}).get("validation")
    if validation:
        summary = validation["summary"]
        status = validation["status"]
        st.metric("Status", status)
        st.metric("Log Entries", summary.get("total_log_entries", 0))
        st.metric("Missing APIs", len(summary.get("missing_apis", [])))

st.divider()

history_response = requests.get(f"{API_BASE_URL}/api/history", timeout=10)
history_items = history_response.json().get("items", []) if history_response.ok else []

left, right = st.columns([1, 2])
with left:
    st.subheader("Recent Activity")
    if history_items:
        st.dataframe(
            [
                {
                    "Time": item["created_at"],
                    "Type": item["event_type"],
                    "Status": item["status"],
                    "Title": item["title"],
                }
                for item in history_items
            ],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No activity yet.")

with right:
    st.subheader("Latest Detail")
    if history_items:
        st.json(history_items[0])
    else:
        st.caption("Upload a flow and log to begin.")
