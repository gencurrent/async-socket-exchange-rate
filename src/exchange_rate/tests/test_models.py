"""
Test Exchange Rate pydantic models
"""

import pytest

from db.models import ExchangeRate
from exchange_rate.models import (
    ExchangeRateAssetHistoryMessageModel,
    ExchangeRatePointModel,
)


@pytest.mark.asyncio
def test_exchange_rate_point_model__json(exchange_rate: ExchangeRate):
    """
    Test the ExchangeRatePointModel model JSON-related functions
    """
    instance = ExchangeRatePointModel.from_exchange_rate(exchange_rate)
    data = instance.model_dump()

    assert data["assetName"] == exchange_rate.asset.name
    assert data["assetId"] == exchange_rate.asset.id
    assert data["time"] == exchange_rate.time
    assert data["value"] == exchange_rate.value


@pytest.mark.asyncio
def test_exchange_rate_asset_history_message_model__json(exchange_rate: ExchangeRate):
    """
    Test the ExchangeRatePointModel model JSON-related functions
    """
    exchange_rate_points = []
    for idx in range(2):
        obj = exchange_rate.model_copy()
        obj.value += idx
        er_model_instance = ExchangeRatePointModel.from_exchange_rate(obj)
        exchange_rate_points.append(er_model_instance)

    instance = ExchangeRateAssetHistoryMessageModel(points=exchange_rate_points)
    data = instance.model_dump()

    # The nested documents are dumped into the JSON-compatible structures
    assert data["points"] == [
        er_point.model_dump() for er_point in exchange_rate_points
    ]
