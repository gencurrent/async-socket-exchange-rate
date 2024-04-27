"""
The Exchange rate application client service to handle the exchange rates logic
"""

import abc
import asyncio
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Coroutine, List

from pymongo import DESCENDING

from db.models import Asset, ExchangeRate
from exchange_rate.models import (
    AssetsMessageModel,
    ExchangeRateAssetHistoryMessageModel,
    ExchangeRatePointModel,
)
from exchange_rate.utils import single_error_rpc_response
from rpc.models import RPCErrorMessageModel, RPCCommandModel


class AbstractExchangeRateClientService(abc.ABC):
    """Abstract exchange rate per client service"""

    @abc.abstractmethod
    async def rpc_assets(self) -> AsyncGenerator[RPCCommandModel, Any]:
        """
        Yield the list of available assets
        """

    @abc.abstractmethod
    async def rpc_switch_asset_id(self, asset_id: int) -> Coroutine:
        """
        Set the new asset by ID
        :param int asset_id: ID of the asset
        """

    @abc.abstractmethod
    async def rpc_subscribe(self) -> AsyncGenerator[RPCCommandModel, Any]:
        """
        Subscribe to the ExchangeRate data for the specified asset:
            get data for last 30 mins;
            listen to the new ExchangeRate records live
        """


class ExchangeRateClientService(AbstractExchangeRateClientService):
    """
    Exchange Rate app client service to handle client-specific data
    """

    def __init__(self):
        """A new instance of ExchangeRateClientService"""
        self._asset: Asset | None = None

    async def rpc_switch_asset_id(self, asset_id: int | None) -> RPCCommandModel | None:
        """
        Set a new asset_id
        :param int | None asset_id: asset ID. Turn off listening if asset_id is None
        """
        # Fetch the Asset record
        if asset_id is None:
            self._asset = None
            return
        asset = await Asset.find_one(Asset.id == asset_id)
        if not asset:
            return single_error_rpc_response(
                action="subscribe", error=f"Asset with id={asset_id} does not exist"
            )
        self._asset = asset

    async def rpc_assets(self) -> AsyncGenerator[RPCCommandModel, Any]:
        """
        Yield the list of available assets
        """
        assets = await self._get_assets()
        message = AssetsMessageModel(assets=assets)
        rpc_message = RPCCommandModel(action="assets", message=message.model_dump())
        yield rpc_message

    async def rpc_subscribe(self) -> AsyncGenerator[RPCCommandModel, Any]:
        """
        Subscribe to the ExchangeRate data for the specified asset:
        get data for last 30 mins
        and listen to the new ExchangeRate records live
        """
        exchange_rates = await self.get_exchange_rate_history()
        if not exchange_rates:
            yield single_error_rpc_response(action="points", error="No points to return")
            return

        # Yield the asset history points message
        points = [ExchangeRatePointModel.from_exchange_rate(er) for er in exchange_rates]
        message = ExchangeRateAssetHistoryMessageModel(points=points)
        yield RPCCommandModel(action="asset_history", message=message.model_dump())

        # Yield new exchange rate points live
        last_er = exchange_rates[0]
        while self._asset:
            exchange_rate = (
                await ExchangeRate.find(
                    ExchangeRate.asset.id == self._asset.id,
                )
                .sort(-ExchangeRate.time)
                .first_or_none()
            )
            # NOTE: Setting `asset` is much faster than fetching links inside the query
            exchange_rate.asset = self._asset

            if exchange_rate and last_er.id != exchange_rate.id:
                last_er = exchange_rate
                message = ExchangeRatePointModel.from_exchange_rate(last_er)
                yield RPCCommandModel(action="point", message=message.model_dump())

            sleep_timedelta = last_er.time + 1 - datetime.now().timestamp()
            if sleep_timedelta > 0:
                await asyncio.sleep(sleep_timedelta)
            else:
                await asyncio.sleep(0.2)

    async def get_exchange_rate_history(self) -> List[ExchangeRate]:
        # Return the past 30 minutes ExchangeRates
        timestamp_from = int((datetime.now() - timedelta(minutes=30)).timestamp())
        exchange_rates = (
            await ExchangeRate.find(
                ExchangeRate.asset.id == self._asset.id,
                ExchangeRate.time >= timestamp_from,
                fetch_links=True,
            )
            .sort(-ExchangeRate.time)
            .to_list()
        )
        return exchange_rates

    async def _get_assets(self) -> List[Asset]:
        """Get a list of assets"""
        return await Asset.find().to_list()
