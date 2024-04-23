from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    The general settings class
    """

    EMCONT_EXCHANGE_RATES_URL: str = Field()

    SERVER_HOST: str = Field(default="0.0.0.0")
    SERVER_PORT: int = Field(default=8000)

    ASSET_LIST: List[str] = Field(default=[])

    # Mongo DB
    MONGO_DB_NAME: str = Field(alias="MONGO_INITDB_DATABASE")
    DATABASE_URI: str = Field(alias="MONGO_CONNECTION_URI")
