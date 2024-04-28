"""
Exchange rate -specific connection service
"""

import asyncio
from abc import ABC, abstractmethod
from json.decoder import JSONDecodeError
from typing import Any, Dict, List

from fastapi import WebSocket
from pydantic import BaseModel, ValidationError
from starlette.websockets import WebSocketState

from exchange_rate.client_service import (
    AbstractExchangeRateClientService,
    ExchangeRateClientService,
)
from rpc.connection_service import AbstractRPCConnectionService, BaseRPCConnectionService
from rpc.models import RPCErrorMessageModel, RPCCommandModel, RPCClientState

SendMessageType = str | Dict[Any, Any] | List[Any] | BaseModel


class AbstractExchangeRateRPCConnectionService(AbstractRPCConnectionService):
    """
    Abstract exchange rates specific per-connection service to handle websocket connection
    """

    @abstractmethod
    def get_exchange_rate_service(self) -> AbstractExchangeRateClientService:
        """Get the exchange rate client service"""


class ExchangeRateRPCConnectionService(
    BaseRPCConnectionService,
    AbstractExchangeRateRPCConnectionService,
):
    """RPC per-connection service to handle websocket connections"""

    def __init__(self, websocket: WebSocket) -> None:
        """Initialize"""
        super().__init__(websocket)

        client_service: AbstractExchangeRateClientService = ExchangeRateClientService()
        self.client_state = RPCClientState(
            client_service=client_service,
            latest_command=None,
            tasks=[],
        )

    def deinitialize(self) -> None:
        """Cancel the pending tasks and deallocate the used resources"""
        self.cancel_all_task()
        self.remove_completed_tasks()

    async def connect(self) -> None:
        """Start accepting messages from the client"""
        await super().connect()

    async def disconnect(self) -> None:
        """Stop accepting messages from the client and deallocate the resources"""
        await super().disconnect()
        self.deinitialize()

    def get_exchange_rate_service(self) -> AbstractExchangeRateClientService:
        """Get the related ExchangeRateClientService"""
        return self.client_state.client_service

    def get_last_rpc_command(self) -> RPCCommandModel | None:
        """Get the last set RPCCommandModel object"""
        return self.client_state.latest_command

    def set_last_rpc_command(self, rpc_command: RPCCommandModel):
        """Set the last RPCCommandModel object"""
        self.client_state.latest_command = rpc_command

    def add_task(self, task: asyncio.Task) -> None:
        """Put a new task into the list to save its reference"""
        self.remove_completed_tasks()
        self.client_state.tasks.append(task)

    def remove_completed_tasks(self) -> None:
        """Remove all the completed tasks"""
        tasks = self.client_state.tasks
        self.client_state.tasks = [task for task in tasks if task and not task.done()]

    def cancel_all_task(self) -> None:
        """Cancel all the tasks from the list of stored tasks"""
        # Remove all the completed tasks
        for task in self.client_state.tasks:
            if task and not task.done():
                task.cancel()
