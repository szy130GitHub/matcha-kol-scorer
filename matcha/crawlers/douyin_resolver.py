"""Douyin handle -> sec_user_id resolver.

Strategy: reuse MediaCrawler's ``DouYinClient.search_info_by_keyword`` with
``SearchChannelType.USER`` to find candidates, then match by:
    1. exact ``unique_id`` (抖音号 field on the profile)
    2. fallback: exact ``nickname`` if ``display_name`` provided

Returns ``ResolveResult`` with status:
    - resolved: single unambiguous match, has sec_user_id
    - not_found: search returned zero candidates
    - ambiguous: multiple unique_id-matching candidates, needs display_name to disambiguate

Note: MediaCrawler doesn't expose USER-channel search out of the box (only GENERAL
in ``core.py``), but ``SearchChannelType.USER`` is defined in ``field.py`` and the
underlying HTTP endpoint accepts it. We call ``search_info_by_keyword`` directly.

Response schema for USER channel (empirically verified — TODO on first live run):
    {
      "data": [
        {
          "type": 4,  # user card type
          "user_list": [
            {
              "user_info": {
                "sec_uid": "MS4wLjABAAAA...",
                "unique_id": "matcha_lover_2024",   # 抖音号
                "nickname": "...",
                "short_id": "...",
                "avatar_thumb": {...},
                "custom_verify": "...",
                "follower_count": 12345,
              }
            },
            ...
          ]
        },
        ...
      ]
    }

This module has NO direct dependency on the ``DouYinClient`` import path yet — it
takes a client instance via DI so it's unit-testable without playwright.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from matcha.stores.resolution_repo import ResolveResult

log = logging.getLogger(__name__)


class DouyinSearchClient(Protocol):
    """Minimal interface expected from MediaCrawler's DouYinClient."""

    async def search_info_by_keyword(
        self,
        keyword: str,
        offset: int = ...,
        search_channel: Any = ...,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ...


def _iter_user_candidates(response: dict[str, Any]):
    """Yield user_info dicts from a USER-channel search response."""
    data = response.get("data") if response else None
    if not isinstance(data, list):
        return
    for item in data:
        if not isinstance(item, dict):
            continue
        user_list = item.get("user_list")
        if not isinstance(user_list, list):
            continue
        for user in user_list:
            if isinstance(user, dict):
                info = user.get("user_info")
                if isinstance(info, dict):
                    yield info


def _build_profile_url(sec_uid: str) -> str:
    return f"https://www.douyin.com/user/{sec_uid}"


def _match_by_unique_id(
    candidates: list[dict[str, Any]], handle: str
) -> list[dict[str, Any]]:
    """Filter candidates whose unique_id (抖音号) exactly matches the handle."""
    handle_lower = handle.lower()
    hits: list[dict[str, Any]] = []
    for c in candidates:
        unique_id = str(c.get("unique_id") or "").strip().lower()
        short_id = str(c.get("short_id") or "").strip().lower()
        if unique_id == handle_lower or short_id == handle_lower:
            hits.append(c)
    return hits


def _match_by_nickname(
    candidates: list[dict[str, Any]], display_name: str
) -> list[dict[str, Any]]:
    return [c for c in candidates if str(c.get("nickname") or "").strip() == display_name]


def _load_search_channel_enum():
    """Load ``SearchChannelType`` from ``media_platform/douyin/field.py``
    WITHOUT triggering ``media_platform/douyin/__init__.py``, which eagerly
    imports playwright via ``core.py``.

    Uses ``importlib.util.spec_from_file_location`` to load the file as an
    isolated module. Cached on the function for reuse.
    """
    if getattr(_load_search_channel_enum, "_cache", None) is not None:
        return _load_search_channel_enum._cache  # type: ignore[attr-defined]

    import importlib.util
    from pathlib import Path

    field_path = (
        Path(__file__).resolve().parent.parent.parent
        / "media_platform"
        / "douyin"
        / "field.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_matcha_douyin_field_isolated", field_path
    )
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(f"Cannot load {field_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _load_search_channel_enum._cache = module.SearchChannelType  # type: ignore[attr-defined]
    return module.SearchChannelType


async def resolve_douyin_handle(
    client: DouyinSearchClient,
    handle: str,
    display_name: str | None = None,
) -> ResolveResult:
    """Resolve a douyin handle (抖音号) to a sec_user_id.

    Args:
        client: A DouYinClient-compatible object with search_info_by_keyword.
        handle: The user-facing douyin handle (e.g. ``matcha_lover_2024``).
        display_name: Optional nickname to disambiguate when unique_id matches
            multiple candidates.

    Returns:
        ResolveResult with status ∈ {resolved, not_found, ambiguous}.
    """
    SearchChannelType = _load_search_channel_enum()

    try:
        response = await client.search_info_by_keyword(
            keyword=handle,
            offset=0,
            search_channel=SearchChannelType.USER,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("douyin search failed for handle=%s: %s", handle, exc)
        return ResolveResult(
            platform="douyin",
            handle=handle,
            display_name=display_name,
            status="not_found",
        )

    candidates = list(_iter_user_candidates(response))
    if not candidates:
        return ResolveResult(
            platform="douyin",
            handle=handle,
            display_name=display_name,
            status="not_found",
        )

    unique_matches = _match_by_unique_id(candidates, handle)

    if len(unique_matches) == 1:
        return _build_resolved(unique_matches[0], handle, display_name)

    if len(unique_matches) > 1:
        if display_name:
            name_matches = _match_by_nickname(unique_matches, display_name)
            if len(name_matches) == 1:
                return _build_resolved(name_matches[0], handle, display_name)
        return ResolveResult(
            platform="douyin",
            handle=handle,
            display_name=display_name,
            status="ambiguous",
            candidates=[_slim_candidate(c) for c in unique_matches],
        )

    # No exact unique_id hit — surface fuzzy matches. Nickname fallback if given.
    if display_name:
        name_matches = _match_by_nickname(candidates, display_name)
        if len(name_matches) == 1:
            return _build_resolved(name_matches[0], handle, display_name)

    return ResolveResult(
        platform="douyin",
        handle=handle,
        display_name=display_name,
        status="not_found",
        candidates=[_slim_candidate(c) for c in candidates[:5]],
    )


def _build_resolved(
    user_info: dict[str, Any], handle: str, display_name: str | None
) -> ResolveResult:
    sec_uid = str(user_info.get("sec_uid") or "").strip()
    if not sec_uid:
        return ResolveResult(
            platform="douyin",
            handle=handle,
            display_name=display_name,
            status="not_found",
        )
    return ResolveResult(
        platform="douyin",
        handle=handle,
        display_name=display_name or (user_info.get("nickname") or None),
        status="resolved",
        resolved_id=sec_uid,
        profile_url=_build_profile_url(sec_uid),
    )


def _slim_candidate(user_info: dict[str, Any]) -> dict[str, Any]:
    """Trim a candidate down to fields useful for human review."""
    return {
        "sec_uid": user_info.get("sec_uid"),
        "unique_id": user_info.get("unique_id"),
        "short_id": user_info.get("short_id"),
        "nickname": user_info.get("nickname"),
        "follower_count": user_info.get("follower_count"),
        "custom_verify": user_info.get("custom_verify"),
    }
