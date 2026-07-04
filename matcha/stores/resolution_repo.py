"""Repository for id_resolution table.

Handles caching of (platform, handle) -> resolved_id + xsec_token mapping.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from matcha.stores.db import get_connection

ResolveStatus = Literal["resolved", "not_found", "ambiguous", "expired"]
Platform = Literal["douyin", "xhs"]


@dataclass(frozen=True)
class ResolveRecord:
    """One row of id_resolution."""

    platform: Platform
    handle: str
    status: ResolveStatus
    resolved_at: str  # ISO8601 UTC
    display_name: str | None = None
    resolved_id: str | None = None
    xsec_token: str | None = None
    xsec_source: str | None = None
    profile_url: str | None = None
    expires_at: str | None = None
    raw_candidates: str | None = None  # JSON string when ambiguous

    @staticmethod
    def now_iso() -> str:
        return (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )


@dataclass
class ResolveResult:
    """In-memory result before persistence — holds the raw candidates list."""

    platform: Platform
    handle: str
    status: ResolveStatus
    resolved_id: str | None = None
    display_name: str | None = None
    xsec_token: str | None = None
    xsec_source: str | None = None
    profile_url: str | None = None
    expires_at: str | None = None
    candidates: list[dict] = field(default_factory=list)  # for ambiguous cases

    def to_record(self) -> ResolveRecord:
        return ResolveRecord(
            platform=self.platform,
            handle=self.handle,
            status=self.status,
            resolved_at=ResolveRecord.now_iso(),
            display_name=self.display_name,
            resolved_id=self.resolved_id,
            xsec_token=self.xsec_token,
            xsec_source=self.xsec_source,
            profile_url=self.profile_url,
            expires_at=self.expires_at,
            raw_candidates=json.dumps(self.candidates, ensure_ascii=False)
            if self.candidates
            else None,
        )


class ResolutionRepo:
    """Repository for id_resolution table."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path) if self._db_path else get_connection()

    def get(self, platform: Platform, handle: str) -> ResolveRecord | None:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM id_resolution WHERE platform = ? AND handle = ?",
                (platform, handle),
            ).fetchone()
            if row is None:
                return None
            return ResolveRecord(**{k: row[k] for k in row.keys()})
        finally:
            conn.close()

    def upsert(self, record: ResolveRecord) -> None:
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO id_resolution
                    (platform, handle, display_name, resolved_id, xsec_token, xsec_source,
                     profile_url, status, resolved_at, expires_at, raw_candidates)
                VALUES
                    (:platform, :handle, :display_name, :resolved_id, :xsec_token, :xsec_source,
                     :profile_url, :status, :resolved_at, :expires_at, :raw_candidates)
                """,
                asdict(record),
            )
            conn.commit()
        finally:
            conn.close()

    def upsert_result(self, result: ResolveResult) -> ResolveRecord:
        record = result.to_record()
        self.upsert(record)
        return record

    def list_by_status(
        self, platform: Platform | None = None, status: ResolveStatus | None = None
    ) -> list[ResolveRecord]:
        conn = self._conn()
        try:
            where: list[str] = []
            args: list[str] = []
            if platform:
                where.append("platform = ?")
                args.append(platform)
            if status:
                where.append("status = ?")
                args.append(status)
            sql = "SELECT * FROM id_resolution"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY platform, handle"
            return [
                ResolveRecord(**{k: row[k] for k in row.keys()})
                for row in conn.execute(sql, args).fetchall()
            ]
        finally:
            conn.close()

    def count_by_status(self, platform: Platform | None = None) -> dict[str, int]:
        conn = self._conn()
        try:
            args: list[str] = []
            sql = "SELECT status, COUNT(*) AS c FROM id_resolution"
            if platform:
                sql += " WHERE platform = ?"
                args.append(platform)
            sql += " GROUP BY status"
            return {row["status"]: row["c"] for row in conn.execute(sql, args).fetchall()}
        finally:
            conn.close()
