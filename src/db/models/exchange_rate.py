"""
The exchange rate domain models
"""

from datetime import datetime
from typing import Annotated

import pymongo
from beanie import Document, Indexed, Insert, Link, Replace, before_event
from beanie.odm.queries.find import FindMany
from beanie.operators import In
from pydantic import Field, NaiveDatetime
from pymongo.errors import BulkWriteError
from pymongo.results import InsertManyResult

from db.models.exceptions import AlreadyPopulatedException
from settings import settings


class Asset(Document):
    """
    Asset model.
    The assumptions:
    - asset documents are not going to be deleted from the DB
    - asset documents will be crated only once
    """

    id: int  # Immutable
    name: Indexed(str, unique=True) = Field()

    @classmethod
    async def initialize_assets(cls, raise_exception=True) -> InsertManyResult:
        """
        Initialize the list of assets from the settings
        :returns InsertManyResult: The insertion result
        :rasises AlreadyPopulatedException: some assets have already been populated
        """
        asset_list = settings.ASSET_LIST
        assets = []
        for idx, asset_name in enumerate(asset_list):
            asset = cls(
                id=idx + 1,
                name=asset_name,
            )
            assets.append(asset)
        try:
            return await cls.insert_many(assets)
        except BulkWriteError as exc:
            if raise_exception:
                raise AlreadyPopulatedException from exc

    @staticmethod
    def find_assets_from_settings() -> FindMany:
        """Find assets from the asset list in settings"""
        return Asset.find(In(Asset.name, settings.ASSET_LIST)).sort(+Asset.id)

    class Settings:
        """Collection settings"""

        name = "asset"


class ExchangeRate(Document):
    """Exchange rate Mongo model"""

    asset: Link[Asset] = Field(description="Asset corresponding with the pair")
    time: int = Field(description="Exact creation timestamp")
    value: float = Field(description="Average rate")

    @before_event(Insert, Replace)
    def validate_time(self):
        """Set time to naive datetime"""
        types_allowed = (datetime, int)
        if not isinstance(self.time, types_allowed):
            raise TypeError(
                f"{self.__class__.__name__}.time must be an instance any of {types_allowed}"
            )
        if isinstance(self.time, datetime):
            self.time = int(self.time.timestamp())

    class Settings:
        """Collection settings"""

        name = "exchangeRate"
        indexes = [
            pymongo.IndexModel(
                [
                    ("asset", pymongo.ASCENDING),
                    ("time", pymongo.ASCENDING),
                ],
                name="assetIdWithTime",
                unique=True,
            ),
            pymongo.IndexModel(
                [
                    ("asset._id", pymongo.ASCENDING),
                ],
                name="asset",
            ),
        ]
