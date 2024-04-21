"""
Pydantic models for server specification
"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from db.models import Asset, ExchangeRate

class EmcontExchangeRate(BaseModel):
    """DTO model"""

    asset: Asset | None = \
        Field(description="The corresponding Asset from the DB")
    symbol: str = Field(alias="Symbol")
    bid: float = Field(alias="Bid")
    ask: float = Field(alias="Ask")
    spread: float = Field(alias="Spread")
    product_type: str = Field(alias="ProductType")
    last_close: float = Field(alias="LastClose")
    price_change: float = Field(alias="PriceChange")
    percent_change: float = Field(alias="PercentChange")
    week_high_52: float = Field(alias="52WeekHigh")
    week_low_52: float = Field(alias="52WeekLow")

    def to_exchange_rate(self) -> ExchangeRate:
        """
        Convert the EmcontExchangeRate model to the generic ExchangeRate DB model
        """
        if self.asset is None:
            raise Exception("Asset must be set to yield an ExchangeRate")
        now = datetime.now()
        now_timestamp = int(now.timestamp())

        value = (self.bid + self.ask) / 2
        
        exchange_rate = ExchangeRate(
            asset=self.asset,
            time=now_timestamp,
            value=value
        )
        return exchange_rate