"""
The main conftest file
"""

from datetime import datetime
from typing import List
from unittest.mock import Mock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from core.constants import EURUSD
from db.models import Asset, ExchangeRate
from settings.settings import Settings


@pytest.fixture(scope="session", autouse=True)
def test_settings():
    settings_mock = Mock(spec=Settings)
    settings_instance = Settings()
    for field in settings_instance.model_fields_set:
        value = getattr(settings_instance, field)
        setattr(settings_mock, field, value)
    settings_mock.MONGO_DB_NAME = f"{Settings().MONGO_DB_NAME}_test"

    with patch("settings.settings.Settings.__new__", lambda self: settings_mock):
        with patch("settings.settings", settings_mock):
            yield


@pytest_asyncio.fixture()
async def db():
    """Use db"""
    from db.database import initialize_database

    db = await initialize_database(multiprocessing_mode=True)
    yield db
    await db.client.drop_database(db)


@pytest_asyncio.fixture()
async def test_client(db) -> TestClient:
    """Yield an test requests client"""
    from app import app

    client = TestClient(app=app, base_url="http://test")
    return client


@pytest_asyncio.fixture()
async def test_async_client(db) -> AsyncClient:
    """Yield an test requests client"""
    from app import app

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture()
async def assets(db) -> List[Asset]:
    """Initialize Assets according to the .env settings"""
    await Asset.initialize_assets()
    return await Asset.find().to_list()


@pytest_asyncio.fixture()
async def asset(assets) -> Asset:
    """Fixture of a single Asset instance"""
    return await Asset.find_one(Asset.name == EURUSD)


@pytest_asyncio.fixture()
async def exchange_rate(asset: Asset) -> ExchangeRate:
    """Fixture of a single ExchangeRate instance"""
    now_timestamp = int(datetime.now().timestamp())
    value = 1.17

    # Successfully create the first exchange rate
    er = await ExchangeRate(
        asset=asset,
        time=now_timestamp,
        value=value,
    ).create()
    return er
