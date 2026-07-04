"""Unit tests for id_resolution repository."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from matcha.stores.db import init_db
from matcha.stores.resolution_repo import ResolutionRepo, ResolveRecord, ResolveResult


@pytest.fixture
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    init_db(path)
    yield path
    path.unlink(missing_ok=True)
    for suffix in ("-wal", "-shm"):
        Path(str(path) + suffix).unlink(missing_ok=True)


def test_upsert_and_get_roundtrip(tmp_db: Path) -> None:
    repo = ResolutionRepo(tmp_db)
    record = ResolveRecord(
        platform="douyin",
        handle="matcha_test",
        status="resolved",
        resolved_at="2026-07-04T12:00:00Z",
        resolved_id="MS4wLjABAAAA_synthetic",
        profile_url="https://www.douyin.com/user/MS4wLjABAAAA_synthetic",
        display_name="测试昵称",
    )
    repo.upsert(record)
    got = repo.get("douyin", "matcha_test")
    assert got is not None
    assert got.resolved_id == "MS4wLjABAAAA_synthetic"
    assert got.status == "resolved"
    assert got.display_name == "测试昵称"


def test_upsert_replaces(tmp_db: Path) -> None:
    repo = ResolutionRepo(tmp_db)
    repo.upsert(
        ResolveRecord(
            platform="douyin",
            handle="dup",
            status="not_found",
            resolved_at="2026-07-04T12:00:00Z",
        )
    )
    repo.upsert(
        ResolveRecord(
            platform="douyin",
            handle="dup",
            status="resolved",
            resolved_at="2026-07-04T13:00:00Z",
            resolved_id="SEC_XYZ",
        )
    )
    got = repo.get("douyin", "dup")
    assert got is not None
    assert got.status == "resolved"
    assert got.resolved_id == "SEC_XYZ"


def test_get_missing_returns_none(tmp_db: Path) -> None:
    repo = ResolutionRepo(tmp_db)
    assert repo.get("douyin", "does_not_exist") is None


def test_upsert_result_serializes_candidates(tmp_db: Path) -> None:
    repo = ResolutionRepo(tmp_db)
    result = ResolveResult(
        platform="douyin",
        handle="ambig",
        status="ambiguous",
        candidates=[
            {"sec_uid": "AAA", "nickname": "甲"},
            {"sec_uid": "BBB", "nickname": "乙"},
        ],
    )
    record = repo.upsert_result(result)
    assert record.status == "ambiguous"
    got = repo.get("douyin", "ambig")
    assert got is not None
    assert got.raw_candidates is not None
    assert "AAA" in got.raw_candidates


def test_count_by_status(tmp_db: Path) -> None:
    repo = ResolutionRepo(tmp_db)
    for i in range(3):
        repo.upsert(
            ResolveRecord(
                platform="douyin",
                handle=f"resolved_{i}",
                status="resolved",
                resolved_at="2026-07-04T12:00:00Z",
                resolved_id=f"SEC_{i}",
            )
        )
    repo.upsert(
        ResolveRecord(
            platform="douyin",
            handle="nf",
            status="not_found",
            resolved_at="2026-07-04T12:00:00Z",
        )
    )
    repo.upsert(
        ResolveRecord(
            platform="xhs",
            handle="xhs_1",
            status="resolved",
            resolved_at="2026-07-04T12:00:00Z",
            resolved_id="XHS_1",
        )
    )
    counts_dy = repo.count_by_status("douyin")
    assert counts_dy["resolved"] == 3
    assert counts_dy["not_found"] == 1
    counts_all = repo.count_by_status()
    assert counts_all["resolved"] == 4


def test_list_by_status_filters(tmp_db: Path) -> None:
    repo = ResolutionRepo(tmp_db)
    repo.upsert(
        ResolveRecord(
            platform="douyin",
            handle="a",
            status="resolved",
            resolved_at="2026-07-04T12:00:00Z",
            resolved_id="SEC_A",
        )
    )
    repo.upsert(
        ResolveRecord(
            platform="douyin",
            handle="b",
            status="not_found",
            resolved_at="2026-07-04T12:00:00Z",
        )
    )
    resolved = repo.list_by_status("douyin", "resolved")
    assert len(resolved) == 1
    assert resolved[0].handle == "a"
    not_found = repo.list_by_status("douyin", "not_found")
    assert len(not_found) == 1
    assert not_found[0].handle == "b"
