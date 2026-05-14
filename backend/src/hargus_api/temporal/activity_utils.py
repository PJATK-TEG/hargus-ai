"""Helpers for Temporal activities (heartbeats during long async work)."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

from temporalio import activity

T = TypeVar("T")


async def heartbeat_while(
    coro: Coroutine[Any, Any, T],
    *,
    interval_seconds: float = 60.0,
) -> T:
    """Run *coro* and call ``activity.heartbeat()`` every *interval_seconds* until it finishes.

    Use for LLM or other work that may exceed the workflow's ``heartbeat_timeout`` without
    yielding, so Temporal does not treat the worker as stuck.
    """
    task = asyncio.create_task(coro)
    try:
        while True:
            done, _ = await asyncio.wait(
                {task},
                timeout=interval_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if task in done:
                return task.result()
            activity.heartbeat()
    except asyncio.CancelledError:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        raise
