"""
Emcont (emcont.com) service class
"""

import json
import re
from typing import Any, Dict, List

import httpx
from beanie.exceptions import RevisionIdWasChanged
from beanie.operators import Set
from loguru import logger as _LOG
from pymongo.errors import DuplicateKeyError

from async_tasks.emcont_service.models import EmcontExchangeRate
from db.models.exchange_rate import Asset, ExchangeRate
from settings import settings


class EmcontService:
    """Emcont service to manage functions related to tasks"""

    def __init__(self):
        """Init"""
        self.URL = settings.EMCONT_EXCHANGE_RATES_URL
        self._regex_comp = re.compile(r"null\((?P<content>.*)\);")
        self._assets: List[Asset] = []
        self._client = httpx.AsyncClient()

    async def sync_assets(self) -> None:
        """Synchronize the available assets from the DB"""
        self._assets = await Asset.find_assets_from_settings().to_list()
        if self._assets:
            return
        await Asset.initialize_assets(raise_exception=False)
        self._assets = await Asset.find_assets_from_settings().to_list()

    def _extract_rates(self, text) -> List[Any]:
        """
        Extract array of exchange rates from the endpoint response text
        """
        match = self._regex_comp.match(text)
        if not match:
            raise Exception("Can not extract data from the resource content")
        content = match["content"]
        json_content = json.loads(content)
        rates = json_content["Rates"]
        return rates

    async def fetch_exchange_rates_data(self) -> List[Any]:
        """
        Get the exchange rates
        """
        if not self._assets:
            return []
        timeout = httpx.Timeout(2.5, connect=2.5)
        response: httpx.Response = await self._client.get(url=self.URL, timeout=timeout)
        return self._extract_rates(response.text)

    @staticmethod
    def exchange_rates_data_to_dict(exchange_rates_data) -> Dict[str, Any]:
        return {er["Symbol"]: er for er in exchange_rates_data}

    async def get_and_save_exchange_rates(self) -> None:
        """
        Synchronize the exchange rates from Emcont to the DB
        """
        if not self._assets:
            _LOG.info(f"Assets are not set")
            return
        exchange_rates_data_list = await self.fetch_exchange_rates_data()
        exchange_rates_data_dict = self.exchange_rates_data_to_dict(exchange_rates_data_list)
        # Find the matching asset
        records_saved_number: int = 0
        for asset in self._assets:
            exchange_rates_data = exchange_rates_data_dict[asset.name]

            emcon_exchange_rate_dto = EmcontExchangeRate(asset=asset, **exchange_rates_data)
            exchange_rate = emcon_exchange_rate_dto.to_exchange_rate()
            try:
                update_query = await ExchangeRate.find_one(
                    ExchangeRate.asset.id == asset.id,
                    ExchangeRate.time == exchange_rate.time,
                ).upsert(
                    Set({}),
                    on_insert=ExchangeRate(
                        asset=asset,
                        time=exchange_rate.time,
                        value=exchange_rate.value,
                    ),
                )
            except DuplicateKeyError:
                continue
            if isinstance(update_query, ExchangeRate):
                exchange_rate = update_query
                records_saved_number += 1

        _LOG.info(f"Successfully saved {records_saved_number} records")
