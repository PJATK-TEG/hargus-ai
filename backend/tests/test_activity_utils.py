"""Tests for Temporal activity helpers."""

from __future__ import annotations

import asyncio

import pytest

from hargus_api.temporal import activity_utils


@pytest.mark.asyncio
async def test_heartbeat_while_heartbeats_during_slow_coro(monkeypatch: pytest.MonkeyPatch) -> None:
    beats: list[None] = []

    def record_heartbeat() -> None:
        beats.append(None)

    monkeypatch.setattr(activity_utils.activity, "heartbeat", record_heartbeat)

    async def slow() -> int:
        await asyncio.sleep(0.15)
        return 7

    result = await activity_utils.heartbeat_while(slow(), interval_seconds=0.05)
    assert result == 7
    assert len(beats) >= 1


@pytest.mark.asyncio
async def test_heartbeat_while_propagates_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(activity_utils.activity, "heartbeat", lambda: None)

    async def boom() -> None:
        raise ValueError("x")

    with pytest.raises(ValueError, match="x"):
        await activity_utils.heartbeat_while(boom(), interval_seconds=0.01)
