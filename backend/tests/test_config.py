import pytest
from pydantic import ValidationError

from hargus_api.config import Settings


def test_temporal_server_url_must_use_host_port_format() -> None:
    with pytest.raises(ValidationError):
        Settings(temporal_server_url="temporal-server")


def test_temporal_server_url_rejects_invalid_port() -> None:
    with pytest.raises(ValidationError):
        Settings(temporal_server_url="localhost:99999")
