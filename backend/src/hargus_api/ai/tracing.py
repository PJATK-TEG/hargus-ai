from __future__ import annotations

from functools import lru_cache
from typing import Any

from hargus_api.config import get_settings


@lru_cache(maxsize=1)
def _get_handler():
    """Return Langfuse CallbackHandler singleton, or None when disabled."""
    settings = get_settings()
    if not settings.langfuse_enabled:
        return None
    from langfuse.langchain import CallbackHandler

    return CallbackHandler(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


def traced_config(run_name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a LangChain runnable config dict with Langfuse tracing when enabled."""
    config: dict[str, Any] = {"run_name": run_name}
    if metadata:
        config["metadata"] = metadata
    handler = _get_handler()
    if handler is not None:
        config["callbacks"] = [handler]
    return config
