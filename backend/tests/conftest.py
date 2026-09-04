from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from immo.config import get_settings
from immo.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    get_settings.cache_clear()
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client
    get_settings.cache_clear()
