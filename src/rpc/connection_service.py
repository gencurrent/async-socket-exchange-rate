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
from rpc.models import RPCErrorMessageModel, RPCCommandModel, RPCClientState

SendMessageType = str | Dict[Any, Any] | List[Any] | BaseModel


class AbstractConnectionService(ABC):
    """
    Abstract per-connection service to handle websocket connection
    """

    @abstractmethod
    async def connect(self) -> None:
        """Start accepting messages from the client"""

    @abstractmethod
    async def disconnect(self) -> None:
        """Stop accepting messages from the client and deallocate the resources"""

    @abstractmethod
    def get_last_rpc_command(self) -> RPCCommandModel:
        """Get the last set RPCCommandModel object"""

    @abstractmethod
    def set_last_rpc_command(self, rpc_command: RPCCommandModel):
        """Set the last RPCCommandModel object"""

    @abstractmethod
    def add_task(self, task: asyncio.Task) -> None:
        """Put a new task into the list of tasks to save its reference"""

    @abstractmethod
    async def receive_command(self) -> RPCCommandModel:
        """Read the incoming RPC commands until a valid command is received"""

    @abstractmethod
    async def send_message(
        self,
        message: SendMessageType,
    ) -> None:
        """Send message"""


class RPCConnectionService:
    """RPC per-connection service to handle websocket connections"""

    def __init__(self, websocket: WebSocket) -> None:
        """Initialize"""
        self._websocket: WebSocket = websocket

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
        await self._websocket.accept()

    async def disconnect(self) -> None:
        """Stop accepting messages from the client and deallocate the resources"""
        if self._websocket.client_state != WebSocketState.DISCONNECTED:
            await self._websocket.close()
        self.deinitialize()

    def get_client_service(self) -> AbstractExchangeRateClientService:
        """Get the related ExchangeRateClientService"""
        return self.client_state.client_service

    def get_last_rpc_command(self) -> RPCCommandModel:
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

    async def receive_command(self) -> RPCCommandModel:
        """Read the incoming JSON RPC command until a valid command is received"""
        while True:
            try:
                json_command = await self._websocket.receive_json()
            except JSONDecodeError:
                await self.send_message("Could not parse the JSON command")
                continue
            if not isinstance(json_command, dict):
                await self.send_message(
                    f"Invalid type of the message: {type(json_command)}. "
                    "Command must be a valid JSON mapping",
                )
                continue
            try:
                rpc_command = RPCCommandModel(**json_command)
            except ValidationError as exception:
                error_message = RPCErrorMessageModel.from_validation_error(exception)
                await self.send_message(error_message)
                continue
            return rpc_command

    async def send_message(
        self,
        message: SendMessageType,
    ) -> None:
        """Send message"""
        if isinstance(message, str):
            await self._websocket.send_text(message)
        elif isinstance(message, BaseModel):
            await self._websocket.send_json(message.model_dump())
        elif isinstance(message, (dict, list)):
            try:
                await self._websocket.send_json(message)
            except TypeError:
                return
        else:
            raise TypeError("Unsupported message type")
