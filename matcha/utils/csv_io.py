"""CSV input parser for `matcha resolve` / `matcha scan`.

Input format (creators.csv):
    platform,handle,display_name,note
    douyin,matcha_lover_2024,,专精抹茶博主
    xhs,tokyo_matcha,东京抹茶研究所,
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Platform = Literal["douyin", "xhs"]
_VALID_PLATFORMS: set[str] = {"douyin", "xhs"}


@dataclass(frozen=True)
class CreatorInput:
    """One row of user-provided CSV, normalized."""

    platform: Platform
    handle: str
    display_name: str | None
    note: str | None
    row_index: int  # 1-based, for error messages


class CsvParseError(Exception):
    """Raised when CSV is malformed."""


def parse_creators_csv(path: Path | str) -> list[CreatorInput]:
    """Parse creators CSV. Skips empty rows. Validates platform enum + handle.

    Raises:
        FileNotFoundError: path doesn't exist
        CsvParseError: missing required columns, invalid platform, empty handle
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")

    inputs: list[CreatorInput] = []
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"platform", "handle"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise CsvParseError(
                f"CSV missing required columns {required}. Got: {reader.fieldnames}"
            )

        for i, row in enumerate(reader, start=2):  # header is row 1
            platform_raw = (row.get("platform") or "").strip().lower()
            handle = (row.get("handle") or "").strip()
            display_name = (row.get("display_name") or "").strip() or None
            note = (row.get("note") or "").strip() or None

            # Skip fully empty rows
            if not platform_raw and not handle:
                continue

            if platform_raw not in _VALID_PLATFORMS:
                raise CsvParseError(
                    f"Row {i}: invalid platform '{platform_raw}', "
                    f"must be one of {sorted(_VALID_PLATFORMS)}"
                )
            if not handle:
                raise CsvParseError(f"Row {i}: handle is empty")

            inputs.append(
                CreatorInput(
                    platform=platform_raw,  # type: ignore[arg-type]
                    handle=handle,
                    display_name=display_name,
                    note=note,
                    row_index=i,
                )
            )

    return inputs


def group_by_platform(
    inputs: list[CreatorInput],
) -> dict[Platform, list[CreatorInput]]:
    """Split into per-platform lists for downstream parallel processing."""
    out: dict[Platform, list[CreatorInput]] = {"douyin": [], "xhs": []}
    for item in inputs:
        out[item.platform].append(item)
    return out
