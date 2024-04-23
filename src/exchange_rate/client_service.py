"""
The Exchange rate application client service to handle the exchange rates logic
"""

import asyncio
from typing import List
from datetime import datetime, timedelta

from fastapi import WebSocket
from loguru import logger as _LOG
from pymongo import DESCENDING

from exchange_rate.models import (
    AssetsMessageModel,
    ExchangeRatePointModel,
    ExchangeRateAssetHistoryMessageModel,
)
from db.models import Asset, ExchangeRate
from rpc.models import RPCMessageModel, RPCErrorMessageModel
from exchange_rate.utils import single_error_rpc_response


class ExchangeRateClientService:

    def __init__(self):

        self._asset: Asset | None = None

    @property
    def asset(self) -> Asset | None:
        """Getter"""
        return self._asset

    @asset.setter
    def asset(self, asset: Asset) -> None:
        """Set the asset"""
        if not isinstance(asset, Asset):
            raise TypeError(f"{Asset} type is required")
        self._asset = asset

    async def rpc_switch_asset_id(self, asset_id: int):
        """Set a new asset_id"""
        if not isinstance(asset_id, int):
            return single_error_rpc_response(
                action="subscribe", error="`assetId` must be integer"
            )
        # Fetch the Asset record
        asset = await Asset.find_one(Asset.id == asset_id)
        if not asset:
            return single_error_rpc_response(
                action="subscribe", error="Asset with id={asset} is not found"
            )
        self.asset = asset

    async def get_assets(self) -> List[Asset]:
        """Get a list of assets"""
        return await Asset.find().to_list()

    async def rpc_assets_message(self):
        """
        Get the list of available assets
        """
        assets = await self.get_assets()
        message = AssetsMessageModel(assets=assets)
        rpc_message = RPCMessageModel(action="assets", message=message.model_dump())
        yield rpc_message

    async def get_exchange_rate_history(self) -> List[ExchangeRate]:
        # Return the past 30 minutes ExchangeRates
        timestamp_from = int((datetime.now() - timedelta(minutes=30)).timestamp())
        exchange_rates = (
            await ExchangeRate.find(
                ExchangeRate.asset.id == self.asset.id,
                ExchangeRate.time >= timestamp_from,
                fetch_links=True,
            )
            .sort(-ExchangeRate.time)
            .to_list()
        )
        return exchange_rates

    async def rpc_subscribe_message(self, websocket: WebSocket):
        """
        Subscribe to the ExchangeRate data for the specified asset:
        get data for last 30 mins
        and listen to the new ExchangeRate records live
        """

        # Yield the asset history points message
        exchange_rates = await self.get_exchange_rate_history()
        points = [
            ExchangeRatePointModel.from_exchange_rate(er) for er in exchange_rates
        ]
        message = ExchangeRateAssetHistoryMessageModel(points=points)
        yield RPCMessageModel(action="asset_history", message=message.model_dump())

        # Yield new exchange rate points live
        if not exchange_rates:
            yield RPCMessageModel(
                action="points", message={"errors": [{"msg": "No points to return"}]}
            )
            return
        last_er = exchange_rates[-1]
        while True:
            exchange_rate = await ExchangeRate.find_one(
                ExchangeRate.asset.id == self.asset.id,
                fetch_links=True,
                sort=[("time", DESCENDING)],
            )

            if exchange_rate and last_er.id != exchange_rate.id:
                last_er = exchange_rate
                message = ExchangeRatePointModel.from_exchange_rate(last_er)
                yield RPCMessageModel(action="point", message=message.model_dump())

            sleep_timedelta = last_er.time + 1 - datetime.now().timestamp()
            if sleep_timedelta > 0:
                await asyncio.sleep(sleep_timedelta)
            else:
                await asyncio.sleep(0.2)
