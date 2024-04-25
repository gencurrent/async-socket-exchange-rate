"""
The async periodic tasks running loop application
"""

import asyncio
import os
import sys
from typing import Any, Dict, Coroutine, Sequence
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


async def periodic(
    interval_sec: float | int = 1,
    pre_sleep_sec: float | int = 0,
    async_function: Coroutine = None,
    args: Sequence[Any] = tuple(),
    kwargs: Dict[Any, Any] = dict(),
):
    """
    Periodic execution function
    :param float | int interval: interval before tasks finishing the task and executing it again
    :param float | int pre_sleep_sec: sleep asynhronously before starting the task
    :param Coroutine async_function: the async function
    :param Sequence[Any] args: positional arguments to pass to `async_function`
    :param Dict[Any, Any] args: key arguments to pass to `async_function`
    """
    await asyncio.sleep(pre_sleep_sec)
    while True:
        # await the target
        try:
            await async_function(*args, **kwargs)
        except Exception as exc:
            _LOG.error(exc)
            raise exc
        await asyncio.sleep(interval_sec)


async def main():
    _LOG.info("Starting creating async workers")
    await initialize_database(skip_indexes=True)
    await EMCONT_SERVICE.sync_assets()

    NUMBER_OF_TASKS = 4
    # Launch the periodic tasks
    task_set = set()
    try:
        async with asyncio.TaskGroup() as task_group:
            for idx in range(NUMBER_OF_TASKS):
                # task = asyncio.create_task(periodic(1 / NUMBER_OF_TASKS, get_and_save_exchnage_rates, idx))
                task = task_group.create_task(
                    periodic(
                        interval_sec=1,
                        pre_sleep_sec=(idx / NUMBER_OF_TASKS),
                        async_function=get_and_save_exchnage_rates,
                        args=(idx,),
                    )
                )
                task_set.add(task)
    except ExceptionGroup as exc_group:
        _LOG.error("The tasks have ended with some exceptions")
        for exc in exc_group.exceptions:
            _LOG.error(exc)


if __name__ == "__main__":
    # Start the event loop
    asyncio.run(main())
