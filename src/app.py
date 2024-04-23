"""
The main file yielding the application instance
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger as _LOG

from db.database import initialize_database
from db.models import Asset
from exchange_rate.routers import router as exchange_rate_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Server lifespan pre- and post- processing function
    """
    _LOG.info("On server initalization")
    await initialize_database()
    await Asset.initialize_assets(raise_exception=False)
    yield
    _LOG.info("On server teardown")


app = FastAPI(lifespan=lifespan)

app.include_router(exchange_rate_router)
