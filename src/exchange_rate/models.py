"""
Exchange rate transformation models
"""

from typing import List

from pydantic import BaseModel, Field, field_validator

from db.models.exchange_rate import Asset, ExchangeRate


class RPCSubscribeMessageModel(BaseModel):
    """
    Data model contained in the `message` field of RPCCommandModel to handle `subscribe`
    """

    asset_id: int = Field(alias="assetId", description="ID of the related Asset")


class ExchangeRatePointModel(BaseModel):
    """Point model related to the ExchangeRate record"""

    assetName: str = Field(alias="asset_name", description="Exchange pair")
    assetId: int = Field(alias="asset_id", description="ID of the related Asset")
    time: int = Field(description="Exchange rate creation time")
    value: float = Field(description="Value")

    @classmethod
    def from_exchange_rate(cls, exchange_rate: ExchangeRate) -> "ExchangeRatePointModel":
        """
        Yield an ExchangeRatePointModel instance from ExchangeRate
        :raises ValueError: if exchange_rate.asset is in the DBLink state
        """
        if not isinstance(exchange_rate.asset, Asset):
            raise ValueError("No Asset assigned to the ExchangeRate object while converting")
        asset = exchange_rate.asset
        result = cls(
            asset_name=asset.name,
            time=exchange_rate.time,
            asset_id=asset.id,  # type: ignore
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
