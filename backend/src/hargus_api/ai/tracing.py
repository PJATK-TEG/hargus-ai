from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

from hargus_api.config import get_settings

logger = logging.getLogger(__name__)


def _sync_langfuse_env_from_settings() -> None:
    """Mirror HARGUS_LANGFUSE_* into LANGFUSE_* for the SDK (same as Langfuse() host/keys)."""
    settings = get_settings()
    host = (settings.langfuse_host or "").rstrip("/")
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
    os.environ["LANGFUSE_HOST"] = host


@lru_cache(maxsize=1)
def _get_handler():
    """Return Langfuse CallbackHandler singleton, or None when disabled.

    Equivalent to docs: ``Langfuse(public_key=..., secret_key=..., host=...)`` — we
    set ``LANGFUSE_*`` env vars then use ``CallbackHandler(public_key=...)`` so
    LangChain runs are traced.
    """
    settings = get_settings()
    if not settings.langfuse_enabled:
        return None

    _sync_langfuse_env_from_settings()

    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler
    except ModuleNotFoundError:
        # Do not crash activities if optional langchain integration is missing.
        logger.exception("Langfuse CallbackHandler unavailable; continuing without tracing")
        return None

    # Explicitly initialize process-global Langfuse client before creating handler.
    # In some SDK paths, get_client(...) alone can still log "No client initialized".
    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )

    return CallbackHandler(public_key=settings.langfuse_public_key)


def flush_langfuse() -> None:
    """Push buffered observations to Langfuse (important for Temporal activities)."""
    settings = get_settings()
    if not settings.langfuse_enabled or not settings.langfuse_public_key.strip():
        return
    _sync_langfuse_env_from_settings()
    try:
        from langfuse import get_client

        get_client(public_key=settings.langfuse_public_key).flush()
    except Exception:
        logger.exception("Langfuse flush failed")


def traced_config(
    run_name: str,
    metadata: dict[str, Any] | None = None,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Return a LangChain runnable config dict with Langfuse tracing when enabled.

    ``session_id`` and ``user_id`` are forwarded as the documented Langfuse-langchain
    shortcut keys (``langfuse_session_id`` / ``langfuse_user_id``) so all agent
    invocations under a single workflow run group into one Langfuse session.
    """
    config: dict[str, Any] = {"run_name": run_name}
    md: dict[str, Any] = {k: v for k, v in (metadata or {}).items() if v is not None}
    if session_id:
        md["langfuse_session_id"] = session_id
    if user_id:
        md["langfuse_user_id"] = user_id
    if md:
        config["metadata"] = md
    handler = _get_handler()
    if handler is not None:
        config["callbacks"] = [handler]
    return config


def record_score(
    name: str,
    value: float,
    *,
    session_id: str | None = None,
    trace_id: str | None = None,
    comment: str = "",
) -> None:
    """Create a Langfuse score; no-op when Langfuse is disabled.

    Attaches the score to a session (preferred for workflow-level rollups) or
    a specific trace when provided. Failures are swallowed and logged so that
    metric emission never breaks an activity.
    """
    settings = get_settings()
    if not settings.langfuse_enabled or not settings.langfuse_public_key.strip():
        return
    if session_id is None and trace_id is None:
        logger.debug("record_score(%s) skipped: no session_id or trace_id", name)
        return

    _sync_langfuse_env_from_settings()
    try:
        from langfuse import get_client

        client = get_client(public_key=settings.langfuse_public_key)
        kwargs: dict[str, Any] = {"name": name, "value": float(value)}
        if comment:
            kwargs["comment"] = comment
        if trace_id:
            kwargs["trace_id"] = trace_id
        if session_id:
            kwargs["session_id"] = session_id
        client.create_score(**kwargs)
    except Exception:
        logger.exception("Langfuse score emission failed for %s", name)
