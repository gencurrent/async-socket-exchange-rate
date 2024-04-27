"""
Exchange rate application router
"""

import asyncio
from json.decoder import JSONDecodeError
from typing import Any, Coroutine, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger as _LOG
from pydantic import BaseModel, ValidationError

from exchange_rate.client_service import (
    AbstractExchangeRateClientService,
    ExchangeRateClientService,
)
from exchange_rate.models import RPCSubscribeMessageModel
from exchange_rate.utils import single_error_rpc_response
from rpc.models import RPCErrorMessageModel, RPCMessageModel, RPCClientState

ASSET_ID_FIELD = "assetId"

router = APIRouter()


class WebSocketConnectionManager:
    """The connection manager to handle websocket connections"""

    def __init__(self) -> None:
        """Initialize"""
        self._connections: Dict[WebSocket, RPCClientState] = {}

    async def connect(self, websocket: WebSocket) -> None:
        """Initialize the connection with the client"""
        await websocket.accept()
        client_service: AbstractExchangeRateClientService = ExchangeRateClientService()
        client_state = RPCClientState(
            client_service=client_service,
        )

        self._connections[websocket] = client_state

    def disconnect(self, websocket: WebSocket) -> None:
        """Handle the client disconnection"""
        self.cancel_all_task(websocket)
        self.remove_completed_task(websocket)
        del self._connections[websocket]

    def get_client_service(self, websocket: WebSocket) -> AbstractExchangeRateClientService:
        """Get the related ExchangeRateClientService"""
        service: AbstractExchangeRateClientService = self._connections[websocket].client_service
        return service

    def get_last_rpc_command(self, websocket: WebSocket) -> RPCMessageModel:
        """Get the related ExchangeRateClientService"""
        rpc_command = self._connections[websocket].latest_command
        return rpc_command

    def set_last_rpc_command(self, websocket: WebSocket, rpc_command: RPCMessageModel):
        """Get the related ExchangeRateClientService"""
        self._connections[websocket].latest_command = rpc_command

    def put_task(self, websocket: WebSocket, task: asyncio.Task) -> None:
        """Put a new task into the list to save its reference"""
        self.remove_completed_task(websocket)
        self._connections[websocket].tasks.append(task)

    def remove_completed_task(self, websocket: WebSocket) -> None:
        """Remove all the completed tasks"""
        tasks = self._connections[websocket].tasks
        self._connections[websocket].tasks = [task for task in tasks if task and not task.done()]

    def cancel_all_task(self, websocket: WebSocket) -> None:
        """Cancel all the tasks from the list of stored tasks"""
        # Remove all the completed tasks
        for task in self._connections[websocket].tasks:
            if task and not task.done():
                task.cancel()

    async def receive_command(self, websocket: WebSocket) -> RPCMessageModel | None:
        """Read the incoming JSON RPC command until a valid command is received"""
        while True:
            try:
                json_command = await websocket.receive_json()
            except JSONDecodeError:
                await CONNECTION_MANAGER.send_message(websocket, "Could not parse the JSON command")
                continue
            if not isinstance(json_command, dict):
                await CONNECTION_MANAGER.send_message(
                    websocket,
                    f"Invalid type of the message: {type(json_command)}. "
                    "Command must be a valid JSON mapping",
                )
                continue
            try:
                rpc_command = RPCMessageModel(**json_command)
            except ValidationError as exception:
                error_message = RPCErrorMessageModel.from_validation_error(exception)
                await CONNECTION_MANAGER.send_message(websocket, error_message)
                continue
            return rpc_command

    async def send_message(
        self,
        websocket: WebSocket,
        message: str | Dict[Any, Any] | List[Any] | BaseModel,
    ) -> None:
        """Send message"""
        if isinstance(message, str):
            await websocket.send_text(message)
        elif isinstance(message, BaseModel):
            await websocket.send_json(message.model_dump())
        elif isinstance(message, (dict, list)):
            try:
                await websocket.send_json(message)
            except TypeError:
                return
        else:
            raise TypeError("Unsupported message type")


CONNECTION_MANAGER = WebSocketConnectionManager()


@router.websocket("/")
async def exchange_rate(websocket: WebSocket):
    """
    Subscribe to relevant, up-to-date exchange rates
    """
    await CONNECTION_MANAGER.connect(websocket)
    try:
        while True:
            await wait_and_handle_rpc_message(websocket)
    except WebSocketDisconnect:
        pass
    finally:
        CONNECTION_MANAGER.disconnect(websocket)


async def wait_and_handle_rpc_message(websocket: WebSocket) -> None:
    """
    Wawit and handle a new incoming RPC message
    """
    rpc_message: RPCMessageModel | None = await CONNECTION_MANAGER.receive_command(websocket)
    if not rpc_message:
        return

    client_service: AbstractExchangeRateClientService = CONNECTION_MANAGER.get_client_service(
        websocket
    )
    last_rpc_command = CONNECTION_MANAGER.get_last_rpc_command(websocket)
    match (rpc_message.action):

        case "assets":
            if last_rpc_command and last_rpc_command.action == "subscribe":
                await client_service.rpc_switch_asset_id(None)
            async for message in client_service.rpc_assets():
                await CONNECTION_MANAGER.send_message(websocket, message)

        case "subscribe":
            task: asyncio.Task | None = await handle_subscribe_action(websocket, rpc_message)
            CONNECTION_MANAGER.put_task(websocket, task)
        case _:
            error_rpc_response = single_error_rpc_response(rpc_message.action, "Unknown action")
            await CONNECTION_MANAGER.send_message(websocket, error_rpc_response)
            CONNECTION_MANAGER.set_last_rpc_command(websocket, None)

    CONNECTION_MANAGER.set_last_rpc_command(websocket, rpc_message)


async def handle_subscribe_action(
    websocket: WebSocket, rpc_message: RPCMessageModel
) -> asyncio.Task | None:
    try:
        rpc_subscribe_message_model = RPCSubscribeMessageModel(**rpc_message.message)
    except ValidationError as exception:
        error_message = RPCErrorMessageModel.from_validation_error(exception)
        await CONNECTION_MANAGER.send_message(websocket, error_message)
        return

    # Subscribe
    client_service: AbstractExchangeRateClientService = CONNECTION_MANAGER.get_client_service(
        websocket
    )
    error_message = await client_service.rpc_switch_asset_id(rpc_subscribe_message_model.asset_id)
    if error_message:
        await CONNECTION_MANAGER.send_message(websocket, error_message)
        return

    last_rpc_command = CONNECTION_MANAGER.get_last_rpc_command(websocket)
    if last_rpc_command and last_rpc_command.action == "subscribe":
        # Do not proceed if subscribed to another asset ID
        return

    # Wrap the async outputs into a single async function
    async def yield_exchange_rate_messages():
        async for message in client_service.rpc_subscribe():
            await CONNECTION_MANAGER.send_message(websocket, message)

    task = asyncio.create_task(yield_exchange_rate_messages())
    return task
