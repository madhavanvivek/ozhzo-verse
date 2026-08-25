import socket
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


def is_postgres_live():
    try:
        s = socket.create_connection(("127.0.0.1", 5432), timeout=0.5)
        s.close()
        return True
    except Exception:
        return False


HAS_POSTGRES = is_postgres_live()


def pytest_collection_modifyitems(config, items):
    if not HAS_POSTGRES:
        skip_pg = pytest.mark.skip(reason="PostgreSQL not running on localhost:5432 (mocked unit tests run)")
        for item in items:
            if any(name in item.nodeid for name in [
                "test_phase2_",
                "test_phase4_",
                "test_phase5_",
                "test_phase6_",
                "test_phase7_",
                "test_phase8_",
                "test_pilot_",
                "test_inventory_templates_and_units"
            ]):
                item.add_marker(skip_pg)


@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def client(async_client):
    yield async_client
