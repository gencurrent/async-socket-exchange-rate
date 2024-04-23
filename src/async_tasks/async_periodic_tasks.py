"""
The async periodic tasks running loop application
"""

import asyncio
import os
import sys
from datetime import datetime

from loguru import logger as _LOG

# TODO: Improve DX on the root directory
# The application root dir is the parent dir
sys.path.insert(1, os.getcwd())
from async_tasks.emcont_service.service import EmcontService
from db.database import initialize_database

EMCONT_SERVICE = EmcontService()


async def get_and_save_exchnage_rates(task_id):
    await EMCONT_SERVICE.get_and_save_exchange_rates()


async def periodic(interval_sec, async_function, *args, **kwargs):
    """Periodic execution function"""
    while True:
        await asyncio.sleep(interval_sec)
        # await the target
        try:
            await async_function(*args, **kwargs)
        except Exception as exc:
            _LOG.error(exc)


async def main():
    _LOG.info("Starting creating async workers")
    await initialize_database(skip_indexes=True)
    await EMCONT_SERVICE.sync_assets()

    NUMBER_OF_TASKS = 8
    # Launch the periodic tasks
    for idx in range(NUMBER_OF_TASKS):
        task = asyncio.create_task(periodic(1 / NUMBER_OF_TASKS, get_and_save_exchnage_rates, idx))

    while True:
        await asyncio.sleep(0.4)


if __name__ == "__main__":
    # Start the event loop
    asyncio.run(main())
