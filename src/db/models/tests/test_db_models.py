"""
Unit tests for the DB models
"""

from datetime import UTC, datetime

import pytest
from beanie.odm.fields import PydanticObjectId
from beanie.operators import Set
from bson.dbref import DBRef
from pymongo.errors import DuplicateKeyError
from pymongo.results import UpdateResult

from core.constants import EURUSD
from db.models import Asset, ExchangeRate
from db.models.exceptions import AlreadyPopulatedException
from settings import settings


@pytest.mark.asyncio
async def test_asset_model(db):
    """Test the Asset model methods"""
    await Asset(name=EURUSD, id=1).create()

    # Id must be unique
    with pytest.raises(DuplicateKeyError):
        await Asset(name=f"{EURUSD}_NEW", id=1).create()
    # Name must be unique
    with pytest.raises(DuplicateKeyError):
        await Asset(name=EURUSD, id=2).create()


@pytest.mark.asyncio
async def test_asset_model__initialize_assets(db):
    """Test the Asset model initialization"""
    insert_result = await Asset.initialize_assets()
    assert isinstance(insert_result.inserted_ids, list)
    assets = await Asset.find().to_list()
    for asset, inserted_id, asset_name in zip(
        assets, insert_result.inserted_ids, settings.ASSET_LIST
    ):
        assert asset.name == asset_name
        assert asset.id == inserted_id

    # Impossible to initialize the assets again
    with pytest.raises(AlreadyPopulatedException):
        await Asset.initialize_assets()

    # Get Assets listed in the settins
    assets = await Asset.find_assets_from_settings().to_list()

    for asset, asset_name in zip(assets, settings.ASSET_LIST):
        assert asset.name == asset_name


@pytest.mark.asyncio
async def test_exchange_rate_model__get_create(db):
    """Test the exchange rate model on getting and creating it"""
    await Asset.initialize_assets()
    assets = await Asset.find().to_list()
    asset = assets[0]
    now_timestamp = int(datetime.now().timestamp())
    value = 1.17

    # Successfully create the first exchange rate
    er = await ExchangeRate(
        asset=asset,
        time=now_timestamp,
        value=value,
    ).create()

    assert er.time == now_timestamp
    assert er.value == value
    assert isinstance(er.id, PydanticObjectId)

    # Fetch the ExchangeRate instance with the related Asset
    er_found = await ExchangeRate.find(
        ExchangeRate.asset.name == asset.name,
        ExchangeRate.time == now_timestamp,
        fetch_links=True,
    ).first_or_none()

    assert er_found == er
    assert er_found.asset == asset
    assert er_found.asset.name == asset.name

    # Create the same instance
    error = None
    with pytest.raises(DuplicateKeyError) as exc:
        exchange_rate = await ExchangeRate(
            asset=asset,
            time=now_timestamp,
            value=value,
        ).create()
    error = exc.value
    assert error.details["keyValue"] == {
        "asset": DBRef("asset", 1),
        "time": now_timestamp,
    }


@pytest.mark.asyncio
async def test_exchange_rate_model__conditional_create(db):
    """Test the exchange rate model on upserting"""

    # Init assets in-test
    await Asset.initialize_assets()
    assets = await Asset.find().to_list()
    asset = assets[0]
    now_timestamp = int(datetime.now().timestamp())
    value = 1.17

    assert await ExchangeRate.find().first_or_none() is None

    # Create if does not exist
    exchange_rate: ExchangeRate = await ExchangeRate.find_one(
        ExchangeRate.asset.id == asset.id,
        ExchangeRate.time == now_timestamp,
    ).upsert(
        Set({}),
        on_insert=ExchangeRate(
            asset=asset,
            time=now_timestamp,
            value=value,
        ),
    )

    # The only ExchangeRate in the DB is the inserted one
    assert await ExchangeRate.find(fetch_links=True).first_or_none() == exchange_rate

    # Create if does not exist for the 2nd time
    new_value = 2
    update_result: UpdateResult = await ExchangeRate.find_one(
        ExchangeRate.asset.id == asset.id,
        ExchangeRate.time == now_timestamp,
    ).upsert(
        Set({ExchangeRate.value: new_value}),
        on_insert=ExchangeRate(
            asset=asset,
            time=now_timestamp,
            value=value,
        ),
    )

    assert update_result.upserted_id is None
    assert update_result.raw_result["updatedExisting"] is True
    exchange_rate = await ExchangeRate.find(fetch_links=True).first_or_none()
    assert exchange_rate.value == new_value
