"""Unit tests for CSV input parser."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from matcha.utils.csv_io import CsvParseError, group_by_platform, parse_creators_csv


def _write(content: str) -> Path:
    fh = tempfile.NamedTemporaryFile(
        "w", suffix=".csv", delete=False, encoding="utf-8", newline=""
    )
    fh.write(content)
    fh.close()
    return Path(fh.name)


def test_parses_basic_rows() -> None:
    p = _write(
        "platform,handle,display_name,note\n"
        "douyin,matcha_lover,示例A,备注\n"
        "xhs,tokyo_matcha,东京抹茶,\n"
    )
    try:
        inputs = parse_creators_csv(p)
        assert len(inputs) == 2
        assert inputs[0].platform == "douyin"
        assert inputs[0].handle == "matcha_lover"
        assert inputs[0].display_name == "示例A"
        assert inputs[0].note == "备注"
        assert inputs[1].platform == "xhs"
        assert inputs[1].note is None
    finally:
        p.unlink()


def test_skips_empty_rows() -> None:
    p = _write(
        "platform,handle,display_name,note\n"
        "douyin,a,,\n"
        ",,,\n"
        "xhs,b,,\n"
    )
    try:
        inputs = parse_creators_csv(p)
        assert len(inputs) == 2
        assert inputs[0].handle == "a"
        assert inputs[1].handle == "b"
    finally:
        p.unlink()


def test_rejects_invalid_platform() -> None:
    p = _write("platform,handle\nbilibili,x\n")
    try:
        with pytest.raises(CsvParseError, match="invalid platform"):
            parse_creators_csv(p)
    finally:
        p.unlink()


def test_rejects_empty_handle() -> None:
    p = _write("platform,handle\ndouyin,\n")
    try:
        with pytest.raises(CsvParseError, match="handle is empty"):
            parse_creators_csv(p)
    finally:
        p.unlink()


def test_rejects_missing_columns() -> None:
    p = _write("foo,bar\ndouyin,x\n")
    try:
        with pytest.raises(CsvParseError, match="missing required columns"):
            parse_creators_csv(p)
    finally:
        p.unlink()


def test_handles_utf8_bom() -> None:
    """Excel-exported CSVs often start with UTF-8 BOM."""
    p = _write("﻿platform,handle\ndouyin,matcha_x\n")
    try:
        inputs = parse_creators_csv(p)
        assert len(inputs) == 1
        assert inputs[0].handle == "matcha_x"
    finally:
        p.unlink()


def test_group_by_platform() -> None:
    p = _write(
        "platform,handle\n"
        "douyin,a\n"
        "xhs,b\n"
        "douyin,c\n"
        "xhs,d\n"
    )
    try:
        inputs = parse_creators_csv(p)
        grouped = group_by_platform(inputs)
        assert len(grouped["douyin"]) == 2
        assert len(grouped["xhs"]) == 2
        assert [x.handle for x in grouped["douyin"]] == ["a", "c"]
    finally:
        p.unlink()
