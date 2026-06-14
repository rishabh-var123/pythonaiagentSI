"""SQLite persistence for uploads, validations, reports, and history."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "app.db"))


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = _connect()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flow_upload_id INTEGER,
                log_upload_id INTEGER,
                status TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                validation_id INTEGER,
                status TEXT NOT NULL,
                report TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def insert_upload(upload_type: str, filename: str, path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO uploads (type, filename, path, metadata) VALUES (?, ?, ?, ?)",
            (upload_type, filename, str(path), json.dumps(metadata)),
        )
        upload_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM uploads WHERE id = ?", (upload_id,)).fetchone()
        return row_to_dict(row)


def get_upload(upload_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM uploads WHERE id = ?", (upload_id,)).fetchone()
        return row_to_dict(row) if row else None


def get_latest_upload(upload_type: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM uploads WHERE type = ? ORDER BY id DESC LIMIT 1",
            (upload_type,),
        ).fetchone()
        return row_to_dict(row) if row else None


def insert_validation(
    flow_upload_id: int | None,
    log_upload_id: int | None,
    status: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO validations (flow_upload_id, log_upload_id, status, summary)
            VALUES (?, ?, ?, ?)
            """,
            (flow_upload_id, log_upload_id, status, json.dumps(summary)),
        )
        validation_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM validations WHERE id = ?", (validation_id,)).fetchone()
        return row_to_dict(row)


def get_validation(validation_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM validations WHERE id = ?", (validation_id,)).fetchone()
        return row_to_dict(row) if row else None


def get_latest_validation() -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM validations ORDER BY id DESC LIMIT 1").fetchone()
        return row_to_dict(row) if row else None


def insert_report(validation_id: int | None, status: str, report: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO reports (validation_id, status, report) VALUES (?, ?, ?)",
            (validation_id, status, json.dumps(report)),
        )
        report_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        return row_to_dict(row)


def list_history(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT 'upload' AS event_type, id, type AS status, filename AS title, metadata AS payload, created_at
            FROM uploads
            UNION ALL
            SELECT 'validation' AS event_type, id, status, 'Flow validation' AS title, summary AS payload, created_at
            FROM validations
            UNION ALL
            SELECT 'report' AS event_type, id, status, 'RCA report' AS title, report AS payload, created_at
            FROM reports
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [history_row_to_dict(row) for row in rows]


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for key in ("metadata", "summary", "report"):
        if key in item:
            item[key] = json.loads(item[key] or "{}")
    return item


def history_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["payload"] = json.loads(item["payload"] or "{}")
    return item
