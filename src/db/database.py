"""
Database configuration functions
"""

from beanie import init_beanie
from beanie.odm.utils.init import Initializer
from loguru import logger as _LOG
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from db import models as db_models
from settings import settings


class IndexlessBeaineInitializer(Initializer):
    """
    Beanie initializer subclass to skip indexes operations MongoDB indexes
    """

    async def init_indexes(self, cls, allow_index_dropping: bool = False):
        pass


def get_database() -> AsyncIOMotorDatabase:
    """Get the AsyncIOMotorDatabase instance"""
    client = AsyncIOMotorClient(settings.DATABASE_URI)
    database = client[settings.MONGO_DB_NAME]


async def initialize_database(
    skip_indexes: bool = False,
    multiprocessing_mode: bool = False,
) -> AsyncIOMotorDatabase:
    """
    Initialize the database connection and integrate it with Beanie
    """
    client = AsyncIOMotorClient(settings.DATABASE_URI)
    database = client[settings.MONGO_DB_NAME]

    init_kwargs = dict(
        database=database,
        document_models=db_models.__all__,
        multiprocessing_mode=multiprocessing_mode,
    )

    if skip_indexes:
        await IndexlessBeaineInitializer(**init_kwargs)
        return database

    await init_beanie(**init_kwargs)
    return database
