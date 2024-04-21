"""
Exchange rate transformation models
"""

from typing import List
from pydantic import BaseModel, Field

from db.models import Asset, ExchangeRate


class ExchangeRatePointModel(BaseModel):
    """Point model related to the ExchangeRate record"""

    assetName: str = Field(alias="asset_name", description="Exchange pair")
    assetId: int = Field(alias="asset_id", description="ID of the related Asset")
    time: int = Field(description="Exchange rate creation time")
    value: float = Field(description="Value")

    @classmethod
    def from_exchange_rate(
        cls, exchange_rate: ExchangeRate
    ) -> "ExchangeRatePointModel":
        """
        Yield an ExchangeRatePointModel instance from ExchangeRate
        """
        result = cls(
            asset_name=exchange_rate.asset.name,
            time=exchange_rate.time,
            asset_id=exchange_rate.asset.id,
            value=exchange_rate.value,
        )
        return result


class ExchangeRateAssetHistoryMessageModel(BaseModel):
    """Container of the `message` field on `asset_history` action response"""

    points: List[ExchangeRatePointModel] = Field(description="List of Asset points")


class AssetsMessageModel(BaseModel):
    """
    List of Assets - container of the `message` field on the `assets` action response
    """
    assets: List[Asset] = Field(description="List of assets")
