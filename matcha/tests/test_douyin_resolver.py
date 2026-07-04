"""Unit tests for douyin_resolver.

FakeClient — no network, no playwright, no MediaCrawler HTTP layer.
Tests matching logic against synthetic search responses that mirror what
MediaCrawler's ``search_info_by_keyword(channel=USER)`` returns.
"""

from __future__ import annotations

from typing import Any

import pytest

from matcha.crawlers.douyin_resolver import resolve_douyin_handle


class FakeClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    async def search_info_by_keyword(
        self, keyword: str, offset: int = 0, search_channel: Any = None, **kwargs: Any
    ) -> dict[str, Any]:
        self.calls.append(
            {"keyword": keyword, "offset": offset, "search_channel": search_channel}
        )
        return self._response


def _user_response(users: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "data": [
            {"type": 4, "user_list": [{"user_info": u} for u in users]},
        ]
    }


@pytest.mark.asyncio
async def test_resolves_single_unique_id_match() -> None:
    client = FakeClient(
        _user_response(
            [
                {
                    "sec_uid": "MS4wLjABAAAA_target",
                    "unique_id": "matcha_lover_2024",
                    "nickname": "抹茶博主",
                    "follower_count": 12345,
                },
                {
                    "sec_uid": "MS4wLjABAAAA_noise",
                    "unique_id": "other_person",
                    "nickname": "其他人",
                    "follower_count": 100,
                },
            ]
        )
    )
    result = await resolve_douyin_handle(client, "matcha_lover_2024")
    assert result.status == "resolved"
    assert result.resolved_id == "MS4wLjABAAAA_target"
    assert result.display_name == "抹茶博主"
    assert result.profile_url == "https://www.douyin.com/user/MS4wLjABAAAA_target"


@pytest.mark.asyncio
async def test_case_insensitive_unique_id() -> None:
    client = FakeClient(
        _user_response(
            [
                {
                    "sec_uid": "MS4_x",
                    "unique_id": "MATCHA_UpperCase",
                    "nickname": "N",
                }
            ]
        )
    )
    result = await resolve_douyin_handle(client, "matcha_uppercase")
    assert result.status == "resolved"
    assert result.resolved_id == "MS4_x"


@pytest.mark.asyncio
async def test_short_id_fallback() -> None:
    client = FakeClient(
        _user_response(
            [
                {
                    "sec_uid": "MS4_short",
                    "unique_id": "",
                    "short_id": "123456789",
                    "nickname": "N",
                }
            ]
        )
    )
    result = await resolve_douyin_handle(client, "123456789")
    assert result.status == "resolved"
    assert result.resolved_id == "MS4_short"


@pytest.mark.asyncio
async def test_not_found_when_empty_response() -> None:
    client = FakeClient({"data": []})
    result = await resolve_douyin_handle(client, "nonexistent_handle")
    assert result.status == "not_found"
    assert result.resolved_id is None


@pytest.mark.asyncio
async def test_not_found_when_no_unique_id_match_and_no_display_name() -> None:
    client = FakeClient(
        _user_response(
            [
                {"sec_uid": "A", "unique_id": "matcha_lover_2023", "nickname": "旧号"},
                {"sec_uid": "B", "unique_id": "matcha_fan_2024", "nickname": "粉丝号"},
            ]
        )
    )
    result = await resolve_douyin_handle(client, "matcha_lover_2024")
    assert result.status == "not_found"
    assert len(result.candidates) == 2


@pytest.mark.asyncio
async def test_ambiguous_when_multiple_exact_matches() -> None:
    client = FakeClient(
        _user_response(
            [
                {"sec_uid": "A", "unique_id": "same", "nickname": "甲"},
                {"sec_uid": "B", "unique_id": "SAME", "nickname": "乙"},
            ]
        )
    )
    result = await resolve_douyin_handle(client, "same")
    assert result.status == "ambiguous"
    assert len(result.candidates) == 2


@pytest.mark.asyncio
async def test_ambiguous_resolved_by_display_name() -> None:
    client = FakeClient(
        _user_response(
            [
                {"sec_uid": "A", "unique_id": "same", "nickname": "甲"},
                {"sec_uid": "B", "unique_id": "SAME", "nickname": "乙"},
            ]
        )
    )
    result = await resolve_douyin_handle(client, "same", display_name="乙")
    assert result.status == "resolved"
    assert result.resolved_id == "B"


@pytest.mark.asyncio
async def test_nickname_fallback_when_no_unique_id_match() -> None:
    client = FakeClient(
        _user_response(
            [
                {"sec_uid": "A", "unique_id": "matcha_v1", "nickname": "抹茶研究所"},
                {"sec_uid": "B", "unique_id": "matcha_v2", "nickname": "抹茶爱好者"},
            ]
        )
    )
    result = await resolve_douyin_handle(
        client, "matcha_original", display_name="抹茶研究所"
    )
    assert result.status == "resolved"
    assert result.resolved_id == "A"


@pytest.mark.asyncio
async def test_transport_error_returns_not_found() -> None:
    class BrokenClient:
        async def search_info_by_keyword(self, **_: Any) -> dict[str, Any]:
            raise RuntimeError("network timeout")

    result = await resolve_douyin_handle(BrokenClient(), "some_handle")
    assert result.status == "not_found"


@pytest.mark.asyncio
async def test_missing_sec_uid_downgrades_to_not_found() -> None:
    client = FakeClient(
        _user_response([{"sec_uid": "", "unique_id": "target", "nickname": "N"}])
    )
    result = await resolve_douyin_handle(client, "target")
    assert result.status == "not_found"


@pytest.mark.asyncio
async def test_search_call_parameters() -> None:
    from matcha.crawlers.douyin_resolver import _load_search_channel_enum

    SearchChannelType = _load_search_channel_enum()
    client = FakeClient(_user_response([]))
    await resolve_douyin_handle(client, "some_handle")
    assert len(client.calls) == 1
    assert client.calls[0]["keyword"] == "some_handle"
    assert client.calls[0]["search_channel"] == SearchChannelType.USER
